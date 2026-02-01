# Enhancement Summary

## 1. Deterministic Search Ranking
- **Prompt**: "Implement deterministic sorting logic."
- **Before**: Search results were sorted primarily by score, but tie-breaking relied on unstable list order (dependent on `ThreadPool` completion time). Running the same search twice could yield different orders for equal-score items.
- **After**: Implemented a stable sort key `(-score, title, doi, year)`.
- **Behavior**: 100 consecutive runs now produce identical output order (verified by `tests/test_determinism_stress.py`).

## 2. Thread-Safe Atomic Caching
- **Prompt**: "Fix race conditions in cache writes."
- **Before**: `_save_cache` wrote directly to `reference_cache.json` without locking. Concurrent writes (e.g., from parallel web requests) could corrupt the JSON file or cause `JSONDecodeError`. Cache reads returned references to mutable objects.
- **After**: 
  - Writes use `threading.RLock`.
  - Writes occur to a temporary file, then flushed (`fsync`) and atomically moved (`shutil.move`) to the target path.
  - Reads/Writes now return/store `copy.deepcopy` of data to prevent shared state mutation.

## 3. Robust Corporate Author Detection
- **Prompt**: "Improve corporate author detection (e.g., OpenAI, WHO)."
- **Before**: Heuristics missed modern tech entities and acronyms (e.g., "OpenAI", "DeepMind"). "United Nations" was often misparsed as "Nations, U.".
- **After**: Expanded `CORPORATE_KEYWORDS` list to include tech giants and common acronyms. Added specific logic for "United Nations".
- **Behavior**: "United Nations" is preserved as a corporate name. Personal names like "Plato" are not misclassified.

## 4. Search Noise Filtering
- **Prompt**: "Refine noise filtering logic (Option B)."
- **Before**: Any result with a score < 15 was hard-dropped. This caused false negatives for relevant but low-metadata results (e.g., matching author search but low source weight).
- **After**: Contextual filtering applied:
  - **Drop** only if Score < 10 AND no title keyword matches.
  - **Retain (Demote)** if Score is 10-15, acting as a "soft" low-confidence tier.
  - **Prune** strictly if a high-confidence match (>90) is already found.

## 5. Author Name Inversion Handling
- **Prompt**: "Fix search failure for reversed names (e.g., 'Ruvinga Stenford')."
- **Before**: Searching "Surname Given" (e.g., "Ruvinga Stenford") returned 0 results because the parser expected "Given Surname".
- **After**: `search_author_works` now attempts a fallback match with swapped token order if the primary lookup arrives empty.
- **Behavior**: Queries like "Ruvinga Stenford" now correctly retrieve works by "Stenford Ruvinga".

## 6. Normalization Idempotency & Regex
- **Prompt**: "Make normalization idempotent and fix year parsing."
- **Before**: 
  - Calling `normalize()` twice could re-append logs or mangle already-processed names.
  - Regex `\d{4}` stripped suffixes like "2020a" -> "2020".
- **After**: 
  - Added `_normalization_done` flag to prevent re-runs.
  - Updated Year regex to `\d{4}[a-z]?` to preserve disambiguation suffixes.

## 7. Cache Time-To-Live (TTL)
- **Prompt**: "Add 7-day TTL to cache entries."
- **Before**: Cache entries persisted indefinitely, potentially becoming stale.
- **After**: Cache schema updated to `{'timestamp': <float>, 'data': <object>}`. Reads check `time.time() - timestamp > 7_days`; expired entries are treated as misses and auto-refetched.

---

## Known Limitations
*   **External API Variance**: Search determinism is guaranteed *internally*, but if upstream APIs (CrossRef/PubMed) change their returned metadata or ranking for the same query, the final result will naturally vary.
*   **BibTeX Escaping**: The `Export to BibTeX` feature currently does not strictly escape special LaTeX characters in titles, which acts as a minor injection risk for malformed `.bib` files.
*   **Rate Limits**: Parallel searching is aggressive; extremely high throughput might trigger API rate limits (HTTP 429) as there is no built-in exponential backoff.
