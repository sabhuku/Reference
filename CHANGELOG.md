# CHANGELOG

## [Unreleased] - 2026-02-06

### Fixed

#### Critical Fixes
- **[BUG-001]** Fixed parallel search timeout aborting all results
  - Removed outer timeout from `as_completed()` in `parallel_search()`
  - Added explicit `TimeoutError` handling for per-source timeouts
  - Users now receive partial results when one API source times out
  - Files: `src/reference_manager.py`

- **[BUG-002]** Fixed double database insert during migration
  - Corrected indentation in migration logic
  - `db.session.add()` now executes only once per unique reference
  - Prevents duplicate entries and incorrect migration counts
  - Files: `ui/app.py`

- **[BUG-003]** Fixed None-unsafe set comprehension causing crashes
  - Added `if r.title` and `if r.doi` filters to set comprehensions
  - Prevents `AttributeError` when references have NULL titles/DOIs
  - Files: `ui/app.py`

- **[BUG-007]** Fixed unsafe attribute access in migration
  - Wrapped all attribute access with `(value or '')` pattern
  - Migration now handles NULL values in legacy `Reference` objects
  - Files: `ui/app.py`

#### High Priority Fixes
- **[BUG-004]** Fixed migration running on every GET request
  - Added session-based guard using `migration_complete_{user_id}` flag
  - Migration now runs at most once per user session
  - Prevents unnecessary database queries and retry loops
  - Files: `ui/app.py`

- **[BUG-005]** Clarified timeout semantics (auto-resolved by BUG-001 fix)
  - `future.result(timeout=10)` is now the primary timeout mechanism
  - No redundant or misleading timeouts remain
  - Files: `src/reference_manager.py`

#### Code Quality & Observability
- **[BUG-006]** Removed duplicate `author_ambiguity` assignment
  - Eliminated unreachable dead code
  - Files: `src/reference_manager.py`

- **[BUG-008]** Added per-source timing logs to parallel search
  - Logs execution time for each API source
  - Logs total search duration
  - Enables diagnosis of slow or failing APIs
  - Files: `src/reference_manager.py`

### Changed
- Enhanced logging in `parallel_search()` to include timing information
- Improved error messages to show elapsed time on timeouts and errors

### Technical Details
- **Migration Logic**: Now idempotent with session-based completion tracking
- **Search Resilience**: Partial results returned when sources timeout or fail
- **None-Safety**: All attribute access in migration hardened against NULL values
- **Observability**: Per-source and total timing logged for performance analysis

### Files Modified
- `src/reference_manager.py` - Search timeout fix, duplicate code removal, timing logs
- `ui/app.py` - Migration fixes (indentation, None-safety, idempotence)
- `src/utils/ref_normalizer.py` - Dict-to-object normalization (previous session)

### Testing
- Created comprehensive test suite: `test_bug_fixes.py`
- 5/7 automated tests passing
- Manual validation recommended for BUG-001 and BUG-002
- See `TEST_RESULTS.md` for details

---

## Version History

### [Previous] - Pre-2026-02-06
- Initial SQL migration from legacy Bibliography/Reference system
- Dict-to-object normalization layer implementation
