# Deployment Checklist

## Pre-Deployment

### Code Review
- [ ] Review all modified files:
  - [ ] `src/reference_manager.py`
  - [ ] `ui/app.py`
- [ ] Verify fixes match bug descriptions in `bug_ledger.md`
- [ ] Check for any unintended changes

### Testing
- [ ] Run automated test suite: `python tests/test_bug_fixes.py`
- [ ] Review `TEST_RESULTS.md` for manual testing guidance
- [ ] Verify 5/7 automated tests pass
- [ ] Code inspection confirms BUG-001 and BUG-002 fixes

### Documentation
- [ ] Review `CHANGELOG.md` - complete and accurate
- [ ] Review `RELEASE_NOTES.md` - user-facing impact clear
- [ ] Review `COMMIT_TEMPLATE.md` - commit messages ready
- [ ] Ensure `walkthrough.md` documents all fixes

### Version Control
- [ ] Create feature branch: `bugfix/post-migration-fixes`
- [ ] Stage all modified files
- [ ] Commit with message from `COMMIT_TEMPLATE.md`
- [ ] Create annotated tag: `git tag -a v1.0.1-bugfix -m "Post-migration bug fixes"`
- [ ] Push branch and tags to remote

---

## Deployment

### Backup
- [ ] Backup production database
- [ ] Document current application version
- [ ] Note current migration state

### Deploy
- [ ] Pull latest code to staging/production
- [ ] Restart application server
- [ ] Verify application starts without errors

---

## Post-Deployment Validation

### Immediate Checks (5 minutes)
- [ ] Application accessible and responsive
- [ ] No errors in startup logs
- [ ] Homepage loads without crashes

### Manual Testing (30 minutes)

#### BUG-001: Search Timeout Resilience
- [ ] Perform search query
- [ ] Check logs for timing information:
  ```
  INFO: Got X results from crossref in 2.34s
  INFO: Got X results from pubmed in 4.12s
  INFO: Parallel search completed in 10.15s, returned X results
  ```
- [ ] Verify search returns results (not "No results found")

#### BUG-002: No Duplicate Inserts
- [ ] Clear browser session (or use incognito)
- [ ] Login as user with legacy bibliographies
- [ ] Trigger migration by visiting homepage
- [ ] Check database for duplicates:
  ```sql
  SELECT title, COUNT(*) as count 
  FROM project_references 
  GROUP BY title 
  HAVING count > 1;
  ```
- [ ] Expected: Zero rows returned

#### BUG-003: None-Safe Set Comprehension
- [ ] Verify homepage loads without crashes
- [ ] Check logs for no `AttributeError` related to title/DOI

#### BUG-004: Migration Idempotence
- [ ] Visit homepage 5 times in same session
- [ ] Check logs - migration query should appear only once:
  ```
  INFO: MIGRATION: Moved X references from legacy bibliographies
  ```
- [ ] Subsequent visits should skip migration

#### BUG-007: Safe Attribute Access
- [ ] Verify migration completes without crashes
- [ ] Check for references with NULL values in database
- [ ] Confirm migration handled them gracefully

#### BUG-008: Timing Logs
- [ ] Perform multiple searches
- [ ] Verify logs show per-source timing
- [ ] Confirm total search duration logged

---

## Monitoring (First 24 Hours)

### Metrics to Track
- [ ] Search success rate (should improve)
- [ ] Average search response time
- [ ] Migration execution count per user (should be 1)
- [ ] Database duplicate count (should be 0)
- [ ] Application error rate (should decrease)

### Log Analysis
- [ ] Review timing logs for API performance patterns
- [ ] Identify slow APIs (>8s consistently)
- [ ] Check for any new error patterns
- [ ] Verify no regression in existing functionality

### User Feedback
- [ ] Monitor support tickets for search issues
- [ ] Check for reports of duplicate references
- [ ] Verify no new crash reports

---

## Rollback Plan

### If Critical Issues Arise

1. **Immediate Rollback**
   ```bash
   git checkout <previous-version-tag>
   # Restart application
   ```

2. **Database Cleanup** (if BUG-002 created duplicates)
   ```sql
   -- Identify duplicates
   SELECT title, MIN(id) as keep_id, COUNT(*) as count
   FROM project_references
   GROUP BY title
   HAVING count > 1;
   
   -- Remove duplicates (keep oldest)
   DELETE FROM project_references
   WHERE id NOT IN (
     SELECT MIN(id) FROM project_references GROUP BY title
   );
   ```

3. **Clear Migration Flags** (if BUG-004 causes issues)
   - Users can clear browser session/cookies
   - Or manually clear session store on server

### No Database Migrations Required
All changes are code-only. Rollback is safe and simple.

---

## Success Criteria

Deployment is successful when:
- ✅ All manual tests pass
- ✅ No duplicate references in database
- ✅ Search returns partial results on timeout
- ✅ Migration runs once per session
- ✅ Timing logs appear in production logs
- ✅ No increase in error rate
- ✅ No user-reported regressions

---

## Sign-Off

- [ ] Developer: Fixes verified in staging
- [ ] QA: Manual testing complete
- [ ] Operations: Monitoring configured
- [ ] Product: User-facing impact acceptable

**Deployment Date**: _______________  
**Deployed By**: _______________  
**Version**: v1.0.1-bugfix
