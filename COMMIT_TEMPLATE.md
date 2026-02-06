# Git Commit Message Template

## For Individual Bug Fixes

Use this template if committing fixes separately:

```
fix(search): prevent timeout from aborting all results [BUG-001]

- Remove outer timeout from as_completed() in parallel_search()
- Add explicit TimeoutError handling for per-source timeouts
- Users now receive partial results when one API times out

Impact: Critical - prevents "No results found" on slow APIs
Files: src/reference_manager.py
```

```
fix(migration): prevent double database insert [BUG-002]

- Correct indentation in migration logic
- Ensure db.session.add() executes only once per reference
- Prevents duplicate entries and incorrect counts

Impact: Critical - data integrity
Files: ui/app.py
```

```
fix(migration): handle None values in set comprehension [BUG-003]

- Add 'if r.title' and 'if r.doi' filters to set comprehensions
- Prevents AttributeError when references have NULL values

Impact: Critical - prevents homepage crashes
Files: ui/app.py
```

```
fix(migration): add session-based idempotence guard [BUG-004]

- Add migration_complete_{user_id} session flag
- Migration now runs at most once per user session
- Prevents repeated database queries on every GET request

Impact: High - performance improvement
Files: ui/app.py
```

```
fix(migration): safe attribute access for None values [BUG-007]

- Wrap all attribute access with (value or '') pattern
- Migration hardened against NULL values in legacy data

Impact: Critical - prevents migration crashes
Files: ui/app.py
```

```
refactor(search): remove duplicate author_ambiguity assignment [BUG-006]

- Remove unreachable duplicate code block
- Single defensive assignment remains

Impact: Low - code quality
Files: src/reference_manager.py
```

```
feat(observability): add per-source timing logs to search [BUG-008]

- Add timing instrumentation to parallel_search()
- Log per-source execution time and total duration
- Enables diagnosis of slow or failing APIs

Impact: Medium - observability improvement
Files: src/reference_manager.py
```

---

## For Combined Commit

Use this template if committing all fixes together:

```
fix: post-migration bug fixes (8 critical/high issues)

Critical fixes:
- [BUG-001] Prevent search timeout from aborting all results
- [BUG-002] Fix double database insert in migration
- [BUG-003] Handle None values in set comprehension
- [BUG-007] Safe attribute access in migration

High priority:
- [BUG-004] Add session-based migration idempotence
- [BUG-005] Clarify timeout semantics (auto-resolved)

Code quality:
- [BUG-006] Remove duplicate author_ambiguity assignment
- [BUG-008] Add per-source timing logs for observability

Impact:
- Search reliability: Partial results on timeout
- Data integrity: No duplicate inserts
- Stability: No crashes on NULL values
- Performance: Migration runs once per session
- Observability: Timing logs for API diagnosis

Files modified:
- src/reference_manager.py (search timeout, timing, cleanup)
- ui/app.py (migration fixes)

Testing:
- Automated: test_bug_fixes.py (5/7 passing)
- Manual validation recommended
- See TEST_RESULTS.md for details

Refs: bug_ledger.md, walkthrough.md, CHANGELOG.md
```

---

## Git Tag Recommendation

```bash
# Create annotated tag for this release
git tag -a v1.0.1-bugfix -m "Post-migration bug fixes (8 issues)"

# Or use semantic versioning
git tag -a v1.0.1 -m "Bug fix release: migration stability and search resilience"
```

---

## Branch Naming Convention

If using feature branches:
```
bugfix/post-migration-fixes
bugfix/BUG-001-search-timeout
bugfix/BUG-002-double-insert
```

---

## Pull Request Template

```markdown
## Description
Post-migration bug fixes addressing 8 critical and high-priority defects.

## Bug Fixes
- [x] BUG-001: Parallel search timeout resilience
- [x] BUG-002: Double database insert
- [x] BUG-003: None-unsafe set comprehension
- [x] BUG-004: Migration idempotence
- [x] BUG-005: Timeout semantics (auto-resolved)
- [x] BUG-006: Duplicate code removal
- [x] BUG-007: Unsafe attribute access
- [x] BUG-008: Per-source timing logs

## Testing
- [x] Automated tests: `test_bug_fixes.py` (5/7 passing)
- [ ] Manual validation: Search functionality
- [ ] Manual validation: Migration (no duplicates)
- [ ] Manual validation: Log output (timing info)

## Documentation
- [x] CHANGELOG.md updated
- [x] RELEASE_NOTES.md created
- [x] TEST_RESULTS.md created
- [x] bug_ledger.md (detailed analysis)
- [x] walkthrough.md (implementation details)

## Deployment Notes
- No database migrations required
- Backward compatible
- Monitor logs for timing information
- See RELEASE_NOTES.md for deployment checklist

## Reviewers
@team-lead @backend-engineer
```
