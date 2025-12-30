"""Tests for quick win improvements: DOI lookup and Ranking."""
import unittest
from unittest.mock import patch, MagicMock
from src.referencing.referencing import rank_results, lookup_single_work

class TestQuickWins(unittest.TestCase):
    
    # --- Test Search Result Ranking ---
    def test_rank_results(self):
        """Test that results are ranked by relevance."""
        results = [
            {"title": "Unrelated Book", "year": "1990", "doi": ""},
            {"title": "Deep Learning", "year": "2016", "doi": "10.0000/1"}, # Exact title match
            {"title": "Introduction to Deep Learning", "year": "2024", "doi": "10.0000/2"}, # Recent + DOI + Partial
            {"title": "Old Paper about Deep Learning", "year": "2010", "doi": "10.0000/3"}, # DOI + Partial
        ]
        
        ranked = rank_results(results, "Deep Learning")
        
        # Expect "Deep Learning" (exact match) to be first
        self.assertEqual(ranked[0]["title"], "Deep Learning")
        
        # Expect "Introduction..." (Recent + DOI + query in title) to be high
        self.assertEqual(ranked[1]["title"], "Introduction to Deep Learning")
    
    def test_rank_results_recency_boost(self):
        """Test that recent publications get a boost."""
        results = [
            {"title": "Machine Learning", "year": "1990", "doi": ""}, # Score 50 (partial)
            {"title": "Machine Learning", "year": "2023", "doi": ""}, # Score 55 (partial + recent)
        ]
        
        # Note: dict order is not guaranteed, but ranking should sort them
        ranked = rank_results(results, "Machine Learning")
        
        self.assertEqual(ranked[0]["year"], "2023")

    def setUp(self):
        """Set up mock config."""
        self.config_patcher = patch('src.reference_manager.Config')
        self.mock_config = self.config_patcher.start()
        self.mock_config.CROSSREF_MAILTO = "test@example.com"
        # Disable Google Books
        self.mock_config.GOOGLE_BOOKS_API_KEY = ""
        
    def tearDown(self):
        self.config_patcher.stop()

    # --- Test DOI Lookup ---
    @patch('src.api.requests.get')
    def test_doi_lookup_logic(self, mock_get):
        """Test that DOI queries trigger direct lookup."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "title": ["Direct DOI Match"],
                "type": "journal-article",
                "DOI": "10.1234/test",
                "author": [],
                "issued": {"date-parts": [[2023]]}
            }
        }
        mock_get.return_value = mock_response
        
        cache = {}
        # Search with a DOI
        result = lookup_single_work("10.1234/test", cache)
        
        # Verify it called the correct DOI endpoint
        mock_get.assert_called()
        args, kwargs = mock_get.call_args
        # In api.py, url is positional arg
        self.assertTrue("api.crossref.org/works/10.1234/test" in args[0])
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "Direct DOI Match")
    
    @patch('src.referencing.referencing._get_manager')
    def test_non_doi_fallback(self, mock_get_manager):
        """Test that non-DOI queries use manager search."""
        mock_manager = MagicMock()
        mock_manager.cache = {} # Needed for cache update lines
        mock_manager.search_single_work.return_value = None  # Return None to avoid asdict() call on Mock
        mock_get_manager.return_value = mock_manager
        
        cache = {}
        lookup_single_work("Standard Title Search", cache)
        
        mock_manager.search_single_work.assert_called_with("Standard Title Search")

if __name__ == '__main__':
    unittest.main()
