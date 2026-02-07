# Manual Verification Checklist

## Pre-Verification Setup
- [ ] Flask app started
- [ ] Database accessible
- [ ] Logs visible

## BUG-001: Parallel Search Timeout Resilience
- [ ] Perform search query
- [ ] Check logs for timing information
- [ ] Verify partial results returned (not "No results found")

## BUG-002: No Duplicate Database Inserts  
- [ ] Count references before migration
- [ ] Trigger migration
- [ ] Count references after migration
- [ ] Verify count matches expected (no duplicates)

## BUG-003: None-Safe Set Comprehension
- [ ] Check for references with NULL titles in database
- [ ] Trigger migration/homepage load
- [ ] Verify no AttributeError crashes

## BUG-004: Migration Idempotence
- [ ] Clear session/use incognito
- [ ] Visit homepage (triggers migration)
- [ ] Visit homepage 4 more times
- [ ] Check logs - migration should run only once

## BUG-007: Safe Attribute Access
- [ ] Verify migration handles NULL values
- [ ] No crashes during migration
- [ ] Check logs for successful completion

## BUG-008: Per-Source Timing Logs
- [ ] Perform search
- [ ] Check logs for per-source timing
- [ ] Verify format: "Got X results from {source} in Y.YYs"
- [ ] Verify total duration logged

---

## Test Results
**Date**: 2026-02-06  
**Tester**: _______________

### Results Summary
- [ ] All tests passed
- [ ] Issues found (document below)

### Notes:
