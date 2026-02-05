"""
Terminal integration tests for ReferenceManager with project isolation.

Run this BEFORE browser tests to verify core functionality.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.reference_manager import ReferenceManager
from src.models import Publication


def test_singleton_initialization():
    """Verify ReferenceManager initializes with ProjectManager."""
    print("\n" + "="*60)
    print("TEST: ReferenceManager Initialization")
    print("="*60)
    
    mgr = ReferenceManager()
    
    # Check project manager exists
    assert hasattr(mgr, '_project_manager'), "Missing _project_manager attribute"
    assert mgr._project_manager is not None, "ProjectManager is None"
    
    print("[PASS] ReferenceManager has ProjectManager")
    print(f"   Storage path: {mgr._project_manager.storage_path}")
    
    # Check default project auto-creates
    count = mgr.get_project_reference_count("default")
    print(f"[PASS] Default project exists with {count} references")
    
    return mgr


def test_add_reference_isolation(mgr):
    """Verify adding references works and maintains isolation."""
    print("\n" + "="*60)
    print("TEST: Add Reference with Isolation")
    print("="*60)
    
    pub = Publication(
        source="terminal_test",
        pub_type="journal-article",
        authors=["Smith, John"],
        year="2024",
        title="Integration Test Publication",
        journal="Test Journal",
        publisher="",
        location="",
        volume="1",
        issue="1",
        pages="1-10",
        doi="10.1234/test_integration"
    )
    
    initial_count = mgr.get_project_reference_count("default")
    mgr.add_reference_to_project(pub)
    new_count = mgr.get_project_reference_count("default")
    
    assert new_count == initial_count + 1, f"Expected {initial_count + 1}, got {new_count}"
    print(f"[PASS] Reference added (count: {initial_count} -> {new_count})")
    
    # Test isolation via deep copy
    refs = mgr.get_project_references("default")
    original_title = refs[-1].title
    
    # Attempt mutation
    refs[-1].title = "MUTATED_TITLE"
    
    # Verify internal state unchanged
    internal_refs = mgr.get_project_references("default")
    assert internal_refs[-1].title == original_title, "ISOLATION VIOLATED!"
    
    print("[PASS] Deep copy prevents external mutation (isolation preserved)")
    
    return pub


def test_invalid_project_id(mgr):
    """Verify invalid project IDs are rejected."""
    print("\n" + "="*60)
    print("TEST: Invalid Project ID Validation")
    print("="*60)
    
    invalid_ids = [
        "../malicious",
        "test/../../etc",
        "CON",
        "a" * 256  # Too long
    ]
    
    pub = Publication(
        source="test", pub_type="article", authors=[], year="2024",
        title="Test", journal="", publisher="", location="",
        volume="", issue="", pages="", doi=""
    )
    
    for invalid_id in invalid_ids:
        try:
            mgr.add_reference_to_project(pub, project_id=invalid_id)
            print(f"[FAIL] FAILED: '{invalid_id}' was accepted (should reject)")
            return False
        except (ValueError, Exception) as e:
            # Validation can occur in Project.__init__ (ValueError) or
            # ProjectManager.get_or_create_project (ProjectNotFoundError)
            print(f"[PASS] Rejected '{invalid_id[:30]}...'")
    
    return True


def test_nonexistent_project(mgr):
    """Verify accessing nonexistent project raises clear error."""
    print("\n" + "="*60)
    print("TEST: Nonexistent Project Error")
    print("="*60)
    
    try:
        refs = mgr.get_project_references("project_that_does_not_exist")
        print("[FAIL] FAILED: Should have raised ProjectNotFoundError")
        return False
    except Exception as e:
        print(f"[PASS] Raised error: {type(e).__name__}")
        print(f"   Message: {str(e)[:80]}")
        assert "not found" in str(e).lower() or "does not exist" in str(e).lower()
        return True


def test_compliance_check_integration(mgr):
    """Verify compliance check works with project storage."""
    print("\n" + "="*60)
    print("TEST: Compliance Check Integration")
    print("="*60)
    
    # Clear default project first
    mgr.clear_project_references("default")
    
    # Add test publications
    pubs = [
        Publication(
            source="test", pub_type="journal-article",
            authors=["Smith, J."], year="2021", title="First Study",
            journal="Test Journal", publisher="", location="",
            volume="1", issue="1", pages="1-10", doi="10.1/first"
        ),
        Publication(
            source="test", pub_type="journal-article",
            authors=["Jones, A."], year="2022", title="Second Study",
            journal="Test Journal", publisher="", location="",
            volume="2", issue="1", pages="11-20", doi="10.1/second"
        ),
    ]
    
    for pub in pubs:
        mgr.add_reference_to_project(pub)
    
    # Run compliance check on project
    try:
        result = mgr.check_style_compliance(project_id="default")
        
        assert 'results' in result, "Missing 'results' in compliance output"
        assert 'report' in result, "Missing 'report' in compliance output"
        assert 'feedback' in result, "Missing 'feedback' in compliance output"
        assert len(result['results']) == 2, f"Expected 2 results, got {len(result['results'])}"
        
        print(f"[PASS] Compliance check succeeded")
        print(f"   Checked {len(result['results'])} references")
        
        return True
    except Exception as e:
        print(f"[FAIL] Compliance check failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_export_integration(mgr):
    """Verify export functions work with project storage."""
    print("\n" + "="*60)
    print("TEST: Export Integration")
    print("="*60)
    
    # Ensure we have references
    count = mgr.get_project_reference_count("default")
    if count == 0:
        pub = Publication(
            source="test", pub_type="article", authors=["Test, A."],
            year="2024", title="Export Test", journal="Test",
            publisher="", location="", volume="", issue="", pages="", doi=""
        )
        mgr.add_reference_to_project(pub)
    
    # Test BibTeX export
    try:
        bibtex = mgr.export_bibtex()
        assert len(bibtex) > 0, "BibTeX export is empty"
        print(f"[PASS] BibTeX export: {len(bibtex)} characters")
    except Exception as e:
        print(f"[FAIL] BibTeX export failed: {e}")
        return False
    
    # Test RIS export
    try:
        ris = mgr.export_ris()
        assert len(ris) > 0, "RIS export is empty"
        print(f"[PASS] RIS export: {len(ris)} characters")
    except Exception as e:
        print(f"[FAIL] RIS export failed: {e}")
        return False
    
    return True


def run_all_terminal_tests():
    """Run all terminal integration tests."""
    print("\n" + "="*70)
    print(" TERMINAL INTEGRATION TESTS - ReferenceManager + ProjectManager")
    print("="*70)
    
    try:
        # Test 1: Initialization
        mgr = test_singleton_initialization()
        
        # Test 2: Add reference with isolation
        pub = test_add_reference_isolation(mgr)
        
        # Test 3: Invalid project IDs
        if not test_invalid_project_id(mgr):
            return False
        
        # Test 4: Nonexistent project
        if not test_nonexistent_project(mgr):
            return False
        
        # Test 5: Compliance check
        if not test_compliance_check_integration(mgr):
            return False
        
        # Test 6: Export functions
        if not test_export_integration(mgr):
            return False
        
        print("\n" + "="*70)
        print("[PASS] ALL TERMINAL TESTS PASSED")
        print("="*70)
        print("\nNext: Run Flask app and test browser workflows")
        
        return True
        
    except Exception as e:
        print("\n" + "="*70)
        print(f"[FAIL] TERMINAL TESTS FAILED: {e}")
        print("="*70)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_terminal_tests()
    sys.exit(0 if success else 1)
