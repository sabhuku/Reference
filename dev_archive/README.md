# Development Archive

This directory contains **non-production code** that has been quarantined to improve security review clarity.

## Purpose

Before sharing this repository with an external IT security expert, we moved development artifacts here to:

1. **Clarify production attack surface** - Reviewers can focus on `src/`, `ui/`, `modelling/`
2. **Reduce audit noise** - Debug scripts don't obscure production code paths
3. **Preserve historical context** - Tools remain available for reference

## Contents

### `debug/`
One-off diagnostic scripts created to investigate specific bugs:
- Author filtering issues
- Name inversion bugs
- Search result anomalies
- Parsing edge cases

### `verification/`
Post-fix validation scripts that verify correctness after bug fixes:
- Determinism verification
- Idempotence checks
- Metadata validation
- Scoring consistency tests

### `migrations/`
Legacy database migration scripts (already executed):
- Multi-project support migration
- AI remediation database setup
- Initial database creation

### `legacy_launchers/`
Redundant application entry points (superseded by `wsgi.py` and `run_flask.py`):
- Historical launchers from different development phases

### `utilities/`
Development-only utilities (not production tools):
- Analysis scripts
- Data extraction tools
- Investigation helpers

## Production Code

**Production code remains in:**
- `src/` - Core application logic
- `ui/` - Flask web application
- `modelling/` - ML models and training
- `tests/` - Test suite
- `wsgi.py` - Production WSGI entry point
- `scripts/` - Production utilities (documented separately)

## When to Use This Archive

- **Reproducing historical bugs** - Debug scripts show original issue reproduction
- **Understanding past decisions** - Verification scripts demonstrate quality assurance
- **Reference implementations** - Utilities may contain useful patterns

## Security Note

This cleanup was performed to improve auditability. **No runtime behavior was changed.** All production code, tests, and documentation remain untouched.

---

*Archive created: 2026-02-08*  
*Reason: Pre-security-review cleanup*
