import pytest
from unittest.mock import MagicMock, patch
from src.reference_manager import ReferenceManager
from src.models import Publication

class TestRetrievalRanking:
    @pytest.fixture
    def manager(self):
        # Patch Config to avoid loading real files
        with patch('src.reference_manager.Config'):
            mgr = ReferenceManager()
            # Mock APIs
            mgr.crossref = MagicMock()
            mgr.google_books = MagicMock()
            mgr.pubmed = MagicMock()
            mgr.cache = {}
            mgr._save_cache = MagicMock()
            return mgr

    def test_search_works_returns_ranked_limit(self, manager):
        """Test getting multiple ranked results."""
        # Setup mocks to return list of results
        def mock_search(*args, **kwargs):
            return [
                Publication(title="Relevant Book", authors=["Smith"], year="2023", source="crossref", 
                           doi="10.1000/1", pub_type="book", journal="", publisher="", location="",
                           volume="", issue="", pages=""),
                Publication(title="Older Book", authors=["Jones"], year="2010", source="crossref",
                           doi="10.1000/2", pub_type="book", journal="", publisher="", location="",
                           volume="", issue="", pages="")
            ]
        
        manager.crossref.search.return_value = mock_search()
        manager.google_books.search.return_value = []
        manager.pubmed.search.return_value = []
        
        # We need to ensure parallel_search works with the ThreadPoolExecutor
        # For simplicity in unit test, we can patch concurrent.futures.ThreadPoolExecutor 
        # to run synchronously or just let it run (it uses mocks)
        
        # Run search
        results = manager.search_works("Relevant", limit=5)
        
        assert len(results) == 2
        assert results[0].title == "Relevant Book" # Should be first due to recency and title match
        assert results[1].title == "Older Book"

    def test_ranking_logic(self, manager):
        """Test the ranking algorithm explicitly."""
        # Create some publications
        p1 = Publication(title="Machine Learning", authors=["A"], year="2023", source="crossref", doi="1",
                        pub_type="", journal="", publisher="", location="", volume="", issue="", pages="")
        p2 = Publication(title="Machine Learning Basics", authors=["B"], year="2010", source="google_books", doi="", # No DOI
                        pub_type="", journal="", publisher="", location="", volume="", issue="", pages="")
        p3 = Publication(title="Advanced AI", authors=["C"], year="2022", source="crossref", doi="2",
                        pub_type="", journal="", publisher="", location="", volume="", issue="", pages="")

        # Inputs to _rank_results are (Publication, source_str) tuples
        candidates = [
            (p1, 'crossref'), 
            (p2, 'google_books'),
            (p3, 'crossref')
        ]
        
        # Query matches p1 and p2 exactly/partially
        ranked = manager._rank_results(candidates, "Machine Learning")
        
        # p1: Exact title (super high score), recent (+5), DOI (+3), Source (+10) -> High
        # p2: Query in title (+50?), old, no DOI, Source google (+7) -> Medium
        # p3: No title match, recent, DOI -> Low
        
        assert len(ranked) == 3
        assert ranked[0].title == "Machine Learning"
        assert ranked[1].title == "Machine Learning Basics"
        assert ranked[2].title == "Advanced AI"

    def test_search_works_deduplication(self, manager):
        """Test that duplicates are removed but sources are respected."""
        # Same work returned from two sources
        p1 = Publication(title="Same Title", authors=["A"], year="2023", source="crossref", doi="10.123",
                        pub_type="", journal="", publisher="", location="", volume="", issue="", pages="")
        p2 = Publication(title="Same Title", authors=["A"], year="2023", source="pubmed", doi="10.123",
                        pub_type="", journal="", publisher="", location="", volume="", issue="", pages="")
        
        manager.crossref.search.return_value = [p1]
        manager.pubmed.search.return_value = [p2]
        manager.google_books.search.return_value = []
        
        results = manager.search_works("Same Title", limit=5)
        
        assert len(results) == 1
        assert results[0].title == "Same Title"
