# Handle empty normalized_refs in search_pipeline.py

This plan locates the authoritative `search_pipeline.py` module and applies a minimal guard so an empty `normalized_refs` does not raise, while preserving all return types and ordering.

## 1) Locate the correct file
- Confirm the exact path to `search_pipeline.py` in this repo/workspace (it is not currently present in the visible files).
- Once located, open it and trace where `normalized_refs` is constructed and subsequently indexed/iterated in a way that can raise when empty.

### Current findings (workspace search)
- `search_pipeline.py` was not found anywhere under `c:\Users\stenf\Documents\referencing_backup`.
- No `backend/`, `app/`, or `services/` directories are present in this workspace.
- No `search/` directory is present in this workspace.
- No `src/reference/` directory is present (only `src/reference_manager.py` and related modules exist).
- The only `pipeline.py` found is `modelling/pipeline.py`, which appears to be a modelling/compliance pipeline and does not reference `normalized_refs`.

## 2) Implement minimal empty-list guard
- Add the smallest possible conditional check at the point that currently raises (e.g., before `normalized_refs[0]`, `max(...)`, `min(...)`, unpacking, etc.).
- Ensure the guard returns the same *types* currently returned by the function(s) on non-empty inputs, and preserves any tuple/list/dict ordering.
- Do not refactor; do not change behavior for non-empty `normalized_refs`.

## 3) Verify behavior
- Confirm there is no exception when `normalized_refs == []`.
- Sanity-check any callers (if any) for assumptions about non-empty outputs.

## Blocking question
- What is the exact path of `search_pipeline.py` (or the module you refer to), relative to `c:\Users\stenf\Documents\referencing_backup`? If it has been renamed, what is the new filename?

If the file is outside this repo (or is gitignored), please provide one of:
- The absolute path on disk.
- A copy/paste of the file contents.
- The correct in-repo path if it lives under a different top-level folder name.
