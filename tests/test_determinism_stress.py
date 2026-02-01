
import pytest
from unittest.mock import MagicMock
from src.reference_manager import ReferenceManager
from src.models import Publication

# Seeded mock data to simulate identical API responses
MOCK_PUB_1 = Publication(title="Test Pub A", authors=["Smith, J."], year="2020", doi="10.1234/a", source="crossref",
                         pub_type="article", journal="J Test", publisher="", location="", volume="1", issue="1", pages="10")
MOCK_PUB_2 = Publication(title="Test Pub B", authors=["Doe, A."], year="2019", doi="10.1234/b", source="pubmed",
                         pub_type="article", journal="J Med", publisher="", location="", volume="2", issue="2", pages="20")
MOCK_PUB_3 = Publication(title="Test Pub A", authors=["Smith, J."], year="2020", doi="10.1234/a", source="google_books",
                         pub_type="book", journal="", publisher="Press", location="London", volume="", issue="", pages="") # Duplicate of 1
MOCK_PUB_4 = Publication(title="Zebra", authors=["Z.", "A."], year="2021", doi="10.1234/z", source="crossref",
                         pub_type="article", journal="J Zoo", publisher="", location="", volume="", issue="", pages="") # Low score

@pytest.fixture
def manager():
    """Create a ReferenceManager with mocked APIs."""
    mgr = ReferenceManager()
    
    # Mock APIs to return consistent results
    mgr.crossref = MagicMock()
    mgr.crossref.search.return_value = [MOCK_PUB_1, MOCK_PUB_4]
    
    mgr.pubmed = MagicMock()
    mgr.pubmed.search.return_value = [MOCK_PUB_2]
    
    mgr.google_books = MagicMock()
    mgr.google_books.search.return_value = [MOCK_PUB_3]
    
    # Mock parallel_search to use thread pool normally, or mock it?
    # We want to test the full pipeline including threading and sorting.
    # The real parallel_search uses self.crossref etc., so mocking them is enough.
    
    return mgr

def test_determinism_stress_test(manager):
    """
    Execute the same search 100 times.
    Assert that the returned list of publications is IDENTICAL every time.
    """
    query = "Test Pub"
    
    # Run once to establish baseline
    baseline = manager.parallel_search(query)
    baseline_keys = [(p.title, p.doi, p.year) for p in baseline]
    
    print(f"Baseline order: {baseline_keys}")
    
    for i in range(100):
        # Run search
        results = manager.parallel_search(query)
        current_keys = [(p.title, p.doi, p.year) for p in results]
        
        # Check integrity
        # Note: If duplicate detection keeps CrossRef vs GoogleBooks version, it might vary if source weight differs?
        # But we made sorting deterministic.
        # Deduplication implementation: `_deduplicate_results` keeps the first one encountered?
        # Line 641: `seen_dois.add(...)`.
        # `parallel_search` collects all results. `all_results.extend(...)`
        # `as_completed` yields in completion order.
        # So `all_results` order IS non-deterministic before deduplication.
        # `_deduplicate_results` iterates `all_results`. The first one with a DOI wins.
        # IF MOCK_PUB_1 (CrossRef) and MOCK_PUB_3 (GoogleBooks) have same DOI:
        # If CrossRef finishes first: Pub 1 kept. Source = crossref.
        # If GoogleBooks finishes first: Pub 3 kept. Source = google_books.
        # Ranking weights: Crossref=10, GB=7.
        # THIS MEANS SCORE WILL VARY based on thread order!
        # Deterministic sorting only handles TIES. It doesn't fix input variance affecting the Score itself.
        
        # WE NEED TO FIX SOURCE ATTRIBUTION VARIANCE if we want full determinism.
        # Current code logic: deduplication happens before ranking?
        # Check `parallel_search` flow in Phase 1 map:
        # `_deduplicate_results` -> `_rank_results`.
        # So yes, deduplication victim selection depends on thread order.
        # PROPOSED FIX (implicitly required for this test to pass):
        # Sort `all_results` deterministically BEFORE deduplication!
        
        # BUT the task is "Build test". If it fails, it fails, showing the issue.
        # The user asked to "Build... test... Fails if ordering differs."
        # So we should build the test to exposing this.
        
        assert current_keys == baseline_keys, f"Determinism failure at run {i+1}: {current_keys} != {baseline_keys}"

if __name__ == "__main__":
    # Allow running directly
    pytest.main([__file__])
