"""
Verification test for dict → object normalisation fix.

This test demonstrates that the RefObject wrapper correctly enables
attribute access to dictionary data, solving the runtime error:
'dict' object has no attribute 'title'
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.utils.ref_normalizer import normalize_reference, normalize_references, RefObject


def test_refobject_attribute_access():
    """Test that RefObject enables attribute-style access."""
    ref_dict = {
        'title': 'Test Publication',
        'authors': ['Smith, J.', 'Doe, A.'],
        'year': '2024',
        'doi': '10.1234/test',
        'journal': 'Test Journal'
    }
    
    # Normalize dict to object
    ref_obj = normalize_reference(ref_dict)
    
    # Test attribute access (this would fail with plain dict)
    assert ref_obj.title == 'Test Publication'
    assert ref_obj.authors == ['Smith, J.', 'Doe, A.']
    assert ref_obj.year == '2024'
    assert ref_obj.doi == '10.1234/test'
    assert ref_obj.journal == 'Test Journal'
    
    print("✓ Attribute access works correctly")


def test_refobject_dict_compatibility():
    """Test that RefObject maintains dict-style access."""
    ref_dict = {'title': 'Test', 'year': '2024'}
    ref_obj = normalize_reference(ref_dict)
    
    # Test dict-style access (backward compatibility)
    assert ref_obj['title'] == 'Test'
    assert ref_obj.get('year') == '2024'
    assert ref_obj.get('missing', 'default') == 'default'
    assert 'title' in ref_obj
    assert 'missing' not in ref_obj
    
    print("✓ Dict-style access preserved")


def test_idempotent_normalization():
    """Test that normalization is idempotent (safe to apply multiple times)."""
    ref_dict = {'title': 'Test'}
    
    # First normalization
    ref_obj1 = normalize_reference(ref_dict)
    
    # Second normalization (should pass through unchanged)
    ref_obj2 = normalize_reference(ref_obj1)
    
    # Both should work
    assert ref_obj1.title == 'Test'
    assert ref_obj2.title == 'Test'
    
    print("✓ Idempotent normalization works")


def test_batch_normalization():
    """Test batch normalization of reference lists."""
    refs_dicts = [
        {'title': 'Publication 1', 'year': '2023'},
        {'title': 'Publication 2', 'year': '2024'},
        {'title': 'Publication 3', 'year': '2025'}
    ]
    
    # Normalize list
    refs_objs = normalize_references(refs_dicts)
    
    # Test all items
    assert len(refs_objs) == 3
    assert refs_objs[0].title == 'Publication 1'
    assert refs_objs[1].year == '2024'
    assert refs_objs[2].title == 'Publication 3'
    
    print("✓ Batch normalization works")


def test_missing_attributes():
    """Test that missing attributes return None (not KeyError)."""
    ref_dict = {'title': 'Test'}
    ref_obj = normalize_reference(ref_dict)
    
    # Missing attributes should return None
    assert ref_obj.missing_field is None
    assert ref_obj.another_missing is None
    
    print("✓ Missing attributes handled gracefully")


def test_attribute_assignment():
    """Test that attribute assignment works."""
    ref_dict = {'title': 'Original'}
    ref_obj = normalize_reference(ref_dict)
    
    # Modify via attribute
    ref_obj.title = 'Modified'
    assert ref_obj.title == 'Modified'
    
    # Add new attribute
    ref_obj.new_field = 'New Value'
    assert ref_obj.new_field == 'New Value'
    
    print("✓ Attribute assignment works")


def test_type_safety():
    """Test that non-dict objects are rejected."""
    try:
        RefObject("not a dict")
        assert False, "Should have raised TypeError"
    except TypeError as e:
        assert "requires dict" in str(e)
        print("✓ Type safety enforced")


if __name__ == '__main__':
    print("Running dict → object normalisation verification tests...\n")
    
    test_refobject_attribute_access()
    test_refobject_dict_compatibility()
    test_idempotent_normalization()
    test_batch_normalization()
    test_missing_attributes()
    test_attribute_assignment()
    test_type_safety()
    
    print("\n✅ All verification tests passed!")
    print("\nThe normalisation fix correctly:")
    print("  • Enables attribute access (ref.title) on dict data")
    print("  • Preserves backward compatibility with dict methods")
    print("  • Is idempotent (safe to apply multiple times)")
    print("  • Handles missing attributes gracefully")
    print("  • Enforces type safety")
