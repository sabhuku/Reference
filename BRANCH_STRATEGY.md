# Branch Strategy

## Branch Roles

### `main` - Stable Production Baseline
**Purpose:** Last known-good production state  
**Merge Policy:** Only merge after security review approval and completion of MERGE_READINESS.md checklist  
**Deployment:** Production deployments come from this branch  
**Protection:** No direct commits; merge via pull request only

### `bugfix/post-migration-fixes` - Integration/Pre-Release Branch
**Purpose:** Integration branch for security review and next release  
**Content:** Post-migration hardening, bug fixes, documentation improvements  
**Status:** Under security review preparation  
**Merge Target:** Will merge to `main` after approval

## Merge Policy

**Pre-Merge Requirements:**
1. Complete all items in `MERGE_READINESS.md`
2. Obtain security review approval
3. Obtain technical lead approval
4. Create backup branch (`main-pre-merge-backup`)
5. Schedule deployment window

**Merge Process:**
```bash
# 1. Create backup
git checkout main
git branch main-pre-merge-backup

# 2. Merge integration branch
git merge bugfix/post-migration-fixes

# 3. Resolve conflicts (if any)
# 4. Run full test suite
# 5. Push to origin

git push origin main

# 6. Tag release
git tag -a v1.1.0 -m "Post-security-review release"
git push origin v1.1.0
```

## Release Workflow

1. **Development** → `bugfix/post-migration-fixes`
2. **Security Review** → External review of integration branch
3. **Approval** → Complete MERGE_READINESS.md checklist
4. **Integration** → Merge to `main`
5. **Deployment** → Deploy from `main`
6. **Tagging** → Tag release on `main`

## Rollback Plan

If issues arise post-merge:
```bash
# Option 1: Revert merge commit
git revert -m 1 <merge-commit-hash>

# Option 2: Reset to backup
git reset --hard main-pre-merge-backup
git push origin main --force  # Use with extreme caution
```

## Branch Naming Convention

- `main` - Production baseline
- `bugfix/*` - Bug fixes and hardening
- `feature/*` - New features (future)
- `hotfix/*` - Emergency production fixes (future)

## Notes for Security Reviewers

- **Review Target:** `bugfix/post-migration-fixes` branch
- **Baseline:** `main` branch
- **Diff:** 138 files changed (see `merge_analysis.md` in artifacts)
- **Entry Points:** `wsgi.py` (production), `run_flask.py` (development)
- **Quarantine:** `dev_archive/` contains development-only artifacts
