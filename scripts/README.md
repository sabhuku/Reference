# Production Scripts

This directory contains **production utilities** that may be run in deployed environments or as part of operational workflows.

## Scripts

### `create_user.py`
**Purpose**: Create new user accounts for the application  
**When to run**: During initial deployment or when adding new users  
**Production safe**: Yes - creates database records only  
**Usage**: `python scripts/create_user.py`

---

## Adding New Scripts

When adding scripts to this directory:

1. **Document clearly** - Add entry above with purpose, usage, and production safety
2. **Add docstrings** - Include comprehensive module and function docstrings
3. **Consider security** - Scripts here may run in production environments
4. **Test thoroughly** - Production utilities should have corresponding tests

## Development Scripts

Development-only scripts (debug, verification, investigation) belong in `dev_archive/`, not here.

---

*Created: 2026-02-08*  
*Purpose: Clarify production vs. development utilities for security review*
