"""
Isolation verification tests for production-grade hardening.

These tests verify the fixes from the isolation audit:
1. Deep copy prevents external mutation
2. Project ID validation prevents attacks
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models import Publication
from src.project import Project
from src.project_manager import ProjectManager


def test_deep_copy_prevents_mutation():
    """
    Verify that get_references() returns deep copy, preventing mutation.
    
    This addresses the CRITICAL vulnerability from isolation audit.
    """
    project = Project("test", "Test")
    
    pub = Publication(
        source="test",
        pub_type="journal-article",
        authors=["Smith, J."],
        year="2024",
        title="Original Title",
        journal="Test Journal",
        publisher="",
        location="",
        volume="1",
        issue="1", 
        pages="1-10",
        doi="10.1234/test"
    )
    
    project.add_reference(pub)
    
    # Get references (should be deep copy)
    refs = project.get_references()
    
    # Mutate returned object
    refs[0].title = "MUTATED TITLE"
    refs[0].year = "9999"
    
    # Internal state should be UNCHANGED (isolation verified)
    internal_refs = project.get_references()
    assert internal_refs[0].title == "Original Title", (
        f"ISOLATION VIOLATED: Internal title was mutated to '{internal_refs[0].title}'"
    )
    assert internal_refs[0].year == "2024", (
        f"ISOLATION VIOLATED: Internal year was mutated to '{internal_refs[0].year}'"
    )
    
    print("[PASS] Deep copy prevents external mutation (isolation preserved)")


def test_shallow_copy_option_for_performance():
    """
    Verify that deep=False option provides shallow copy for performance.
    """
    project = Project("test", "Test")
    
    pub = Publication(
        source="test",
        pub_type="journal-article",
        authors=["Smith, J."],
        year="2024",
        title="Test",
        journal="Test Journal",
        publisher="",
        location="",
        volume="1",
        issue="1",
        pages="1-10",
        doi="10.1234/test"
    )
    
    project.add_reference(pub)
    
    # Get shallow copy
    refs_shallow = project.get_references(deep=False)
    
    # With shallow copy, mutation WOULD affect internal state
    # (This is expected behavior when caller opts out of safety)
    refs_shallow[0].title = "SHALLOW MUTATED"
    
    # Verify shallow copy behavior
    internal = project.get_references()
    assert internal[0].title == "SHALLOW MUTATED", (
        "deep=False should allow mutation (performance mode)"
    )
    
    print("[PASS] Shallow copy option works (performance mode)")


def test_project_id_validation_path_traversal():
    """
    Verify project_id validation prevents path traversal attacks.
    """
    invalid_ids = [
        "../../../etc/passwd",
        "../malicious",
        "..",
        ".",
        "test/../admin",
        "test/../../root"
    ]
    
    for invalid_id in invalid_ids:
        try:
            Project(invalid_id, "Test")
            assert False, f"Should have rejected '{invalid_id}'"
        except ValueError:
            pass  # Expected - validation rejected the input
    
    print("[PASS] Path traversal attacks rejected")


def test_project_id_validation_reserved_names():
    """
    Verify project_id validation rejects Windows reserved names.
    """
    reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'LPT1']
    
    for reserved in reserved_names:
        try:
            Project(reserved, "Test")
            assert False, f"Should have rejected reserved name '{reserved}'"
        except ValueError as e:
            assert "reserved" in str(e).lower(), f"Wrong error for '{reserved}': {e}"
    
    print("[PASS] Reserved system names rejected")


def test_project_id_validation_length_limit():
    """
    Verify project_id validation enforces length limits.
    """
    too_long = "a" * 256
    
    try:
        Project(too_long, "Test")
        assert False, "Should have rejected overly long ID"
    except ValueError as e:
        assert "long" in str(e).lower() or "255" in str(e), f"Wrong error: {e}"
    
    print("[PASS] Length limit enforced (DoS prevention)")


def test_project_id_validation_special_chars():
    """
    Verify project_id validation rejects SQL injection patterns.
    """
    invalid_ids = [
        "test'; DROP TABLE users; --",
        "test<script>alert(1)</script>",
        "test/malicious",
        "test\\malicious",
        "test\x00null",
    ]
    
    for invalid_id in invalid_ids:
        try:
            Project(invalid_id, "Test")
            assert False, f"Should have rejected '{invalid_id}'"
        except ValueError:
            pass  # Expected
    
    print("[PASS] Special characters and injection patterns rejected")


def test_valid_project_ids():
    """
    Verify that legitimate project IDs are accepted.
    """
    valid_ids = [
        "default",
        "my-project",
        "project_2024",
        "test.project",
        "ABC123",
        "a",
        "123",
        "my-project_v2.0"
    ]
    
    for valid_id in valid_ids:
        try:
            project = Project(valid_id, "Test")
            assert project.id == valid_id
        except ValueError as e:
            assert False, f"Valid ID '{valid_id}' was rejected: {e}"
    
    print("[PASS] Valid project IDs accepted")


def run_isolation_tests():
    """Run all isolation verification tests."""
    print("=" * 60)
    print("ISOLATION HARDENING VERIFICATION")
    print("=" * 60)
    print()
    
    tests = [
        test_deep_copy_prevents_mutation,
        test_shallow_copy_option_for_performance,
        test_project_id_validation_path_traversal,
        test_project_id_validation_reserved_names,
        test_project_id_validation_length_limit,
        test_project_id_validation_special_chars,
        test_valid_project_ids,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {test.__name__}: {e}")
            failed += 1
    
    print()
    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_isolation_tests()
    sys.exit(0 if success else 1)
