# Dict → Object Normalisation Fix

## Problem
References loaded from SQL via `to_publication_dict()` returned plain Python dictionaries, but downstream UI and migration code expected object-style attribute access (e.g., `ref.title`), causing runtime errors:

```
'dict' object has no attribute 'title'
```

## Solution
Introduced a minimal, production-safe normalisation layer in `src/utils/ref_normalizer.py`:

### Core Components

1. **`RefObject` class**: Lightweight wrapper that enables attribute-style access to dict data
   - Supports both `obj.key` and `obj['key']` access patterns
   - Preserves backward compatibility with dict methods (`.get()`, `in` operator)
   - Idempotent: safe to apply multiple times (non-dict objects pass through unchanged)

2. **`normalize_reference(ref)`**: Converts a single dict to `RefObject`
   - Defensive type check: only converts dicts
   - Returns input unchanged if already an object

3. **`normalize_references(refs)`**: Batch normalisation for lists

### Application Points
Applied immediately after SQL load in `ui/app.py`:

- **Line 458**: `get_session_refs()` - Session reference retrieval
- **Line 576**: `index()` route - Main reference loading for authenticated users
- **Line 662**: `index()` route - Post-migration reload from legacy bibliographies
- **Line 691**: `index()` route - Post-migration reload from session
- **Line 1060**: `login()` route - Deduplication during login migration

### Design Principles
✅ **Minimal**: Single-file, ~120 lines, zero external dependencies  
✅ **Deterministic**: No side effects, preserves all dict keys and values  
✅ **Idempotent**: Safe to apply multiple times  
✅ **Backward Compatible**: Works with existing `is_duplicate()` and other utilities  
✅ **Production-Safe**: Defensive type checking, no silent failures  

### Why This Approach?
- **No refactoring required**: UI templates and migration logic unchanged
- **No schema changes**: Database models untouched
- **No ORM introduction**: Stays within existing architecture
- **Single point of change**: All normalization in one module
- **Future-proof**: Easy to remove if UI is refactored to use dict access

### Maintainer Note
This adapter bridges a data-model mismatch between SQL deserialization (dicts) and UI expectations (objects). If UI code is refactored to use dict-style access (`ref['title']`), this module can be safely removed.
