# Manual Verification Guide - Bug Fixes

**Flask App Status**: ✅ Running on http://localhost:5000  
**Date**: 2026-02-06  
**Verification Session**: Post-Migration Bug Fixes

---

## Setup

1. **Open your browser** and navigate to: `http://localhost:5000`
2. **Login** to your account (or create one if needed)
3. **Keep this terminal open** to monitor logs

---

## Test 1: BUG-008 - Per-Source Timing Logs

**What we're testing**: Timing information appears in logs for each API source

### Steps:
1. Navigate to the search page
2. Search for: `"Machine Learning"`
3. **Check the terminal/logs** for output like:
   ```
   INFO: Got 5 results from crossref in 2.34s
   INFO: Got 3 results from pubmed in 4.12s
   INFO: Timeout from google_books after 10.01s
   INFO: Parallel search completed in 10.15s, returned 8 results
   ```

### Expected Result:
- ✅ Each source shows timing: `"Got X results from {source} in Y.YYs"`
- ✅ Total duration logged: `"Parallel search completed in X.XXs"`
- ✅ Timeouts show elapsed time: `"Timeout from {source} after X.XXs"`

### Actual Result:
- [ ] PASS - Timing logs present
- [ ] FAIL - Missing timing information

**Notes**: _______________________________________________

---

## Test 2: BUG-001 - Partial Results on Timeout

**What we're testing**: Search returns results even if one API times out

### Steps:
1. Perform the same search: `"Machine Learning"`
2. Wait for results to appear
3. Check if you got ANY results (even if one source timed out)

### Expected Result:
- ✅ Results displayed (not "No results found")
- ✅ Results from successful sources (CrossRef, PubMed) shown
- ✅ Logs show which source timed out

### Actual Result:
- [ ] PASS - Got partial results
- [ ] FAIL - No results or error

**Number of results received**: _______________

---

## Test 3: BUG-004 - Migration Runs Once Per Session

**What we're testing**: Migration executes only once per user session

### Steps:
1. **Clear your browser session** (Ctrl+Shift+Delete or use Incognito mode)
2. Login again
3. Visit the homepage (this triggers migration)
4. **Check logs** for: `INFO: MIGRATION: Moved X references`
5. Refresh the homepage **4 more times** (F5)
6. **Check logs again** - migration message should NOT appear again

### Expected Result:
- ✅ Migration log appears on first visit
- ✅ NO migration log on subsequent visits (2-5)
- ✅ Session flag prevents re-execution

### Actual Result:
- [ ] PASS - Migration ran once
- [ ] FAIL - Migration ran multiple times

**Migration log count**: _______________

---

## Test 4: BUG-002 - No Duplicate Database Inserts

**What we're testing**: Migration doesn't create duplicate references

### Steps:
1. **Before migration**: Note the number of references in your project
2. **Trigger migration** (clear session, login, visit homepage)
3. **After migration**: Check the reference count again
4. **Run SQL query** to check for duplicates:
   ```sql
   SELECT title, COUNT(*) as count 
   FROM project_references 
   GROUP BY title 
   HAVING count > 1;
   ```

### Expected Result:
- ✅ Reference count increased by expected amount (no doubles)
- ✅ SQL query returns **zero rows** (no duplicates)

### Actual Result:
- [ ] PASS - No duplicates found
- [ ] FAIL - Duplicates detected

**References before**: _______________  
**References after**: _______________  
**Expected increase**: _______________  
**Actual increase**: _______________  
**Duplicates found**: _______________

---

## Test 5: BUG-003 & BUG-007 - None-Safety

**What we're testing**: App handles NULL titles/DOIs without crashing

### Steps:
1. **Check database** for references with NULL titles:
   ```sql
   SELECT COUNT(*) FROM project_references WHERE title IS NULL;
   ```
2. Visit the homepage
3. Trigger migration (if not already done)
4. **Check for crashes** in logs (look for `AttributeError`)

### Expected Result:
- ✅ No `AttributeError` in logs
- ✅ Homepage loads successfully
- ✅ Migration completes without crashes

### Actual Result:
- [ ] PASS - No crashes, NULL values handled
- [ ] FAIL - AttributeError or crash

**NULL titles in DB**: _______________  
**Errors in logs**: _______________

---

## SQL Verification Queries

Run these in your database client to verify data integrity:

### Check for Duplicate References
```sql
SELECT title, COUNT(*) as count 
FROM project_references 
GROUP BY title 
HAVING count > 1;
```
**Expected**: 0 rows

### Check for NULL Titles
```sql
SELECT COUNT(*) FROM project_references WHERE title IS NULL;
```
**Result**: _______________

### Check Migration Count
```sql
SELECT COUNT(*) FROM project_references;
```
**Result**: _______________

---

## Overall Test Results

| Test | Bug ID | Status | Notes |
|------|--------|--------|-------|
| Timing Logs | BUG-008 | ⬜ | |
| Partial Results | BUG-001 | ⬜ | |
| Migration Once | BUG-004 | ⬜ | |
| No Duplicates | BUG-002 | ⬜ | |
| None-Safety | BUG-003, BUG-007 | ⬜ | |

**Legend**: ✅ Pass | ❌ Fail | ⬜ Not Tested

---

## Summary

**All Tests Passed**: [ ] YES [ ] NO

**Issues Found**:
- 
- 
- 

**Next Steps**:
- [ ] All tests passed → Proceed to production deployment
- [ ] Issues found → Document and fix before deployment

**Verified By**: _______________  
**Date**: _______________
