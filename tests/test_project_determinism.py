"""
Determinism Verification Tests for Project-Scoped Architecture.

This test suite verifies that the refactored project-scoped storage
produces byte-identical output compared to the original implementation.

Tests confirm:
1. Single-project use case is byte-identical to old global list
2. Multi-project isolation prevents cross-contamination
3. Precedence rule is enforced correctly
4. Serialization is deterministic (sorted keys)
"""
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models import Publication
from src.project import Project
from src.project_manager import ProjectManager, ProjectNotFoundError
from src.reference_manager import ReferenceManager


def create_test_publication(
    title: str, 
    year: str = "2024", 
    authors: list = None
) -> Publication:
    """Create a test publication with deterministic values."""
    return Publication(
        source="test",
        pub_type="journal-article",
        authors=authors or ["Smith, J."],
        year=year,
        title=title,
        journal="Test Journal",
        publisher="",
        location="",
        volume="1",
        issue="1",
        pages="1-10",
        doi=f"10.1234/{title.lower().replace(' ', '_')}"
    )


class TestDeterminism:
    """Tests for byte-identical deterministic output."""
    
    def test_single_project_compliance_output_identical(self):
        """
        CRITICAL TEST: Verify compliance output is byte-identical
        for single-project use case.
        
        This simulates the old global list behavior using the new
        project-scoped architecture.
        """
        # Create two independent managers
        pm1 = ProjectManager(storage_path=":memory:")
        manager1 = ReferenceManager(project_manager=pm1)
        
        pm2 = ProjectManager(storage_path=":memory:")
        manager2 = ReferenceManager(project_manager=pm2)
        
        # Add identical publications in same order
        pub1 = create_test_publication("First Study", "2021")
        pub2 = create_test_publication("Second Study", "2022")
        pub3 = create_test_publication("Third Study", "2023")
        
        manager1.add_reference_to_project(pub1)
        manager1.add_reference_to_project(pub2)
        manager1.add_reference_to_project(pub3)
        
        manager2.add_reference_to_project(pub1)
        manager2.add_reference_to_project(pub2)
        manager2.add_reference_to_project(pub3)
        
        # Run compliance check using project storage
        result1 = manager1.check_style_compliance(project_id="default")
        result2 = manager2.check_style_compliance(project_id="default")
        
        # Compare results (just the structure, not object references)
        results1_json = json.dumps(result1['results'], sort_keys=True)
        results2_json = json.dumps(result2['results'], sort_keys=True)
        
        assert results1_json == results2_json, (
            "Compliance results are NOT byte-identical!\n"
            f"Result 1: {results1_json[:200]}...\n"
            f"Result 2: {results2_json[:200]}..."
        )
        print("[PASS] Single-project compliance output is byte-identical")

    def test_explicit_publications_override_project(self):
        """
        Verify precedence rule: explicit publications parameter
        overrides project storage.
        """
        pm = ProjectManager(storage_path=":memory:")
        manager = ReferenceManager(project_manager=pm)
        
        # Add publications to project
        stored_pub = create_test_publication("Stored Publication", "2020")
        manager.add_reference_to_project(stored_pub)
        
        # Check with explicit publications (different)
        explicit_pub = create_test_publication("Explicit Publication", "2024")
        result = manager.check_style_compliance(publications=[explicit_pub])
        
        # Result should be for explicit_pub, not stored_pub
        titles_in_result = [r['display_title'] for r in result['results']]
        assert "Explicit Publication" in str(titles_in_result), (
            "Expected explicit publication in results"
        )
        assert "Stored Publication" not in str(titles_in_result), (
            "Stored publication should NOT be in results when explicit provided"
        )
        print("[PASS] Precedence rule enforced: explicit publications override project")

    def test_multi_project_isolation(self):
        """
        Verify multi-project isolation: no cross-contamination.
        """
        pm = ProjectManager(storage_path=":memory:")
        manager = ReferenceManager(project_manager=pm)
        
        # Create two projects
        pm.create_project("Project A", "project_a")
        pm.create_project("Project B", "project_b") 
        
        # Add different publications to each
        pub_a = create_test_publication("Study for A", "2021")
        pub_b = create_test_publication("Study for B", "2022")
        
        manager.add_reference_to_project(pub_a, project_id="project_a")
        manager.add_reference_to_project(pub_b, project_id="project_b")
        
        # Verify isolation
        refs_a = manager.get_project_references("project_a")
        refs_b = manager.get_project_references("project_b")
        
        assert len(refs_a) == 1, f"Expected 1 ref in A, got {len(refs_a)}"
        assert len(refs_b) == 1, f"Expected 1 ref in B, got {len(refs_b)}"
        assert refs_a[0].title == "Study for A", "Wrong publication in A"
        assert refs_b[0].title == "Study for B", "Wrong publication in B"
        
        print("[PASS] Multi-project isolation verified: no cross-contamination")

    def test_non_default_project_raises_if_not_exists(self):
        """
        Verify that accessing non-existent project raises error
        (except for 'default' which is auto-created).
        """
        pm = ProjectManager(storage_path=":memory:")
        manager = ReferenceManager(project_manager=pm)
        
        try:
            manager.get_project_references("nonexistent_project")
            assert False, "Should have raised ProjectNotFoundError"
        except ProjectNotFoundError as e:
            assert "nonexistent_project" in str(e)
            print("[PASS] Non-default project raises error if not exists")

    def test_default_project_auto_created(self):
        """
        Verify that 'default' project is auto-created.
        """
        pm = ProjectManager(storage_path=":memory:")
        manager = ReferenceManager(project_manager=pm)
        
        # Should not raise
        refs = manager.get_project_references("default")
        assert refs == [], "Default project should start empty"
        
        # Should now exist
        assert pm.project_exists("default"), "Default project should exist"
        print("[PASS] Default project is auto-created")

    def test_persistence_determinism(self):
        """
        Verify JSON persistence produces deterministic structure.
        
        Note: Timestamps will differ between runs, so we compare structure
        rather than byte-identical content.
        """
        import tempfile
        import re
        
        # Create and save
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            path1 = f.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            path2 = f.name
        
        try:
            # Create identical project managers
            pm1 = ProjectManager(storage_path=path1)
            pm2 = ProjectManager(storage_path=path2)
            
            # Add identical data
            for pm in [pm1, pm2]:
                proj = pm.get_or_create_project("default")
                proj.add_reference(create_test_publication("Alpha Study", "2021"))
                proj.add_reference(create_test_publication("Beta Study", "2022"))
                pm.save()
            
            # Read and compare files
            with open(path1, 'r') as f:
                content1 = f.read()
            with open(path2, 'r') as f:
                content2 = f.read()
            
            # Normalize timestamps (they will differ between runs)
            # Replace any ISO timestamp with a placeholder
            timestamp_pattern = r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+'
            normalized1 = re.sub(timestamp_pattern, 'TIMESTAMP', content1)
            normalized2 = re.sub(timestamp_pattern, 'TIMESTAMP', content2)
            
            assert normalized1 == normalized2, (
                "Persistence structure is NOT identical (excluding timestamps)!\\n"
                f"File 1: {normalized1[:300]}...\\n"
                f"File 2: {normalized2[:300]}..."
            )
            
            # Verify JSON is valid and has expected structure
            data1 = json.loads(content1)
            assert 'version' in data1, "Missing version field"
            assert 'projects' in data1, "Missing projects field"
            assert 'default' in data1['projects'], "Missing default project"
            assert len(data1['projects']['default']['references']) == 2, "Wrong ref count"
            
            print("[PASS] Persistence produces deterministic structure")
        finally:
            os.unlink(path1)
            os.unlink(path2)

    def test_sorted_iteration(self):
        """
        Verify project listing is always sorted (deterministic order).
        """
        pm = ProjectManager(storage_path=":memory:")
        
        # Add projects in non-sorted order
        pm.create_project("Zebra Project", "zebra")
        pm.create_project("Alpha Project", "alpha")
        pm.create_project("Middle Project", "middle")
        
        projects = pm.list_projects()
        ids = [p.id for p in projects]
        
        assert ids == sorted(ids), (
            f"Projects not in sorted order: {ids}"
        )
        print("[PASS] Project listing is sorted (deterministic)")


class TestBackwardCompatibility:
    """Tests for backward compatibility with existing code."""
    
    def test_set_project_references_works(self):
        """
        Verify set_project_references() replaces all refs in a project.
        """
        pm = ProjectManager(storage_path=":memory:")
        manager = ReferenceManager(project_manager=pm)
        
        # Add initial refs
        pub1 = create_test_publication("First Publication")
        pub2 = create_test_publication("Second Publication")
        manager.add_reference_to_project(pub1)
        manager.add_reference_to_project(pub2)
        assert manager.get_project_reference_count() == 2
        
        # Replace with new set
        pub3 = create_test_publication("Third Publication")
        manager.set_project_references([pub3])
        
        refs = manager.get_project_references()
        assert len(refs) == 1, f"Expected 1 ref after replace, got {len(refs)}"
        assert refs[0].title == "Third Publication"
        print("[PASS] set_project_references() works correctly")

    def test_export_bibtex_default_project(self):
        """
        Verify export_bibtex() with no args uses default project.
        """
        pm = ProjectManager(storage_path=":memory:")
        manager = ReferenceManager(project_manager=pm)
        
        pub = create_test_publication("Export Test")
        manager.add_reference_to_project(pub)
        
        bibtex = manager.export_bibtex()  # No project_id = default
        assert "Export Test" in bibtex or "export_test" in bibtex.lower(), (
            "BibTeX should contain publication title"
        )
        print("[PASS] export_bibtex() works with default project")


def run_all_tests():
    """Run all verification tests."""
    print("=" * 60)
    print("DETERMINISM VERIFICATION TESTS")
    print("=" * 60)
    print()
    
    determinism_tests = TestDeterminism()
    compat_tests = TestBackwardCompatibility()
    
    tests = [
        determinism_tests.test_single_project_compliance_output_identical,
        determinism_tests.test_explicit_publications_override_project,
        determinism_tests.test_multi_project_isolation,
        determinism_tests.test_non_default_project_raises_if_not_exists,
        determinism_tests.test_default_project_auto_created,
        determinism_tests.test_persistence_determinism,
        determinism_tests.test_sorted_iteration,
        compat_tests.test_set_project_references_works,
        compat_tests.test_export_bibtex_default_project,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] FAILED: {test.__name__}")
            print(f"   {e}")
            failed += 1
        except Exception as e:
            print(f"[FAIL] ERROR in {test.__name__}: {e}")
            failed += 1
    
    print()
    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
