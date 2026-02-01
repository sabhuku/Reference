import pytest
from unittest.mock import MagicMock, patch
from src.reference_manager import ReferenceManager
from src.models import Publication

class TestFilterRefactor:
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
            return mgr

    def test_filter_passing(self, manager):
        """Verify filters are passed to API methods."""
        manager.crossref.search.return_value = []
        manager.pubmed.search.return_value = []
        manager.google_books.search.return_value = []
        
        manager.search_works(
            "test query", 
            year_from=2020, 
            year_to=2022, 
            document_type="article",
            language="en",
            open_access=True
        )
        
        # CrossRef should receive year and type
        manager.crossref.search.assert_called_with(
            "test query", 5, 
            year_from=2020, year_to=2022, doc_type="article"
        )
        
        # PubMed should receive year, language, OA
        manager.pubmed.search.assert_called_with(
            "test query", 5,
            year_from=2020, year_to=2022, language="en", open_access=True
        )
        
        # Google Books should receive language
        manager.google_books.search.assert_called_with(
            "test query", 5,
            language="en"
        )

    def test_fallback_filtering_year(self, manager):
        """Verify _filter_results enforces year range."""
        # Create dummy publications
        p1 = Publication(source="mock", pub_type="article", authors=["A"], year="2019", title="Old", journal="", publisher="", location="", volume="", issue="", pages="", doi="")
        p2 = Publication(source="mock", pub_type="article", authors=["B"], year="2021", title="Target", journal="", publisher="", location="", volume="", issue="", pages="", doi="")
        p3 = Publication(source="mock", pub_type="article", authors=["C"], year="2023", title="New", journal="", publisher="", location="", volume="", issue="", pages="", doi="")
        
        # Mock parallel_search internals? No, assume parallel_search calls _filter_results.
        # But we can test _filter_results directly or via search_works if we mock the APIs to return these.
        
        manager.crossref.search.return_value = [p1, p2, p3]
        manager.pubmed.search.return_value = []
        manager.google_books.search.return_value = []
        
        # Search with range 2020-2022
        results = manager.search_works("test", year_from=2020, year_to=2022)
        
        # Should only keep p2 (2021)
        # p1 (2019) is too old
        # p3 (2023) is too new
        assert len(results) == 1
        assert results[0].title == "Target"

    def test_fallback_filtering_type(self, manager):
        """Verify _filter_results enforces document type."""
        p1 = Publication(source="mock", pub_type="article", authors=["A"], year="2021", title="Article", journal="", publisher="", location="", volume="", issue="", pages="", doi="")
        p2 = Publication(source="mock", pub_type="book", authors=["B"], year="2021", title="Book", journal="", publisher="", location="", volume="", issue="", pages="", doi="")
        
        manager.crossref.search.return_value = [p1, p2]
        manager.pubmed.search.return_value = []
        manager.google_books.search.return_value = []
        
        # Search for article
        results = manager.search_works("test", document_type="article")
        
        assert len(results) == 1
        assert results[0].title == "Article"
