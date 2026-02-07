"""
Reference Normalizer - Production-Safe Dict → Object Adapter

This module provides a minimal normalizer to bridge the gap between
SQL-loaded reference dictionaries and UI code expecting attribute access.

Context:
- SQL rows are deserialized into Python dicts via `to_publication_dict()`
- Downstream UI/migration code assumes object-style access (e.g., ref.title)
- This adapter ensures compatibility without refactoring existing code

Design:
- Lightweight wrapper class with __getattr__ for attribute access
- Idempotent: safe to apply multiple times (non-dict objects pass through)
- Deterministic: no side effects, preserves all dict keys and values
- Zero external dependencies
"""


class RefObject:
    """
    Lightweight wrapper that enables attribute-style access to dict data.
    
    Converts dict['key'] access patterns into obj.key patterns without
    modifying the underlying data structure.
    """
    
    def __init__(self, data):
        """
        Initialize from dictionary.
        
        Args:
            data: Dictionary containing reference fields
        """
        if not isinstance(data, dict):
            raise TypeError(f"RefObject requires dict, got {type(data)}")
        self.__dict__['_data'] = data
    
    def __getattr__(self, name):
        """
        Enable attribute access to dictionary keys.
        
        Args:
            name: Attribute name to retrieve
            
        Returns:
            Value from underlying dict, or None if key doesn't exist
        """
        return self._data.get(name)
    
    def __setattr__(self, name, value):
        """
        Enable attribute assignment to dictionary keys.
        
        Args:
            name: Attribute name to set
            value: Value to assign
        """
        if name == '_data':
            self.__dict__['_data'] = value
        else:
            self._data[name] = value
    
    def __getitem__(self, key):
        """Preserve dict-style access for backward compatibility."""
        return self._data[key]
    
    def __setitem__(self, key, value):
        """Preserve dict-style assignment for backward compatibility."""
        self._data[key] = value
    
    def get(self, key, default=None):
        """Preserve dict.get() method for backward compatibility."""
        return self._data.get(key, default)
    
    def __contains__(self, key):
        """Support 'in' operator."""
        return key in self._data
    
    def __repr__(self):
        """String representation for debugging."""
        return f"RefObject({self._data})"


def normalize_reference(ref):
    """
    Normalize a reference to support attribute access.
    
    This adapter exists because SQL-loaded references are plain dicts,
    but UI code expects object-style attribute access (ref.title).
    
    Args:
        ref: Reference object (dict or already-normalized object)
        
    Returns:
        RefObject with attribute access support
        
    Notes:
        - Idempotent: safe to call multiple times
        - Non-dict objects pass through unchanged
        - Preserves all original keys and values
    """
    # Defensive type check: only convert dicts
    if isinstance(ref, dict):
        return RefObject(ref)
    
    # Already normalized or is an object with attributes
    return ref


def normalize_references(refs):
    """
    Normalize a list of references.
    
    Args:
        refs: List of reference objects (dicts or objects)
        
    Returns:
        List of normalized RefObject instances
    """
    return [normalize_reference(ref) for ref in refs]
