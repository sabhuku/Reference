
import unittest
from unittest.mock import patch, MagicMock
from src.reference_manager import ReferenceManager
from src.referencing import referencing
from tests.harness.mock_data import STD_ARTICLE, AMBIGUOUS_AUTHORS, MISSING_DATE

class TestSystemHarness(unittest.TestCase):
    
    def setUp(self):
        self.manager = ReferenceManager()
        # Ensure clean state
        self.manager.cache = {} 
        self.manager.refs = []

    # ------------------------------------------------------------------------
    # 1. Retrieval Correctness (Mocked)
    # ------------------------------------------------------------------------
    @patch('src.api.CrossRefAPI.search')
    def test_retrieval_aggregation(self, mock_search):
        """Verify manager aggregates results from mocked APIs."""
        mock_search.return_value = [STD_ARTICLE]
        
        # We need to patch parallel_search or the individual APIs. 
        # ReferenceManager.search_works calls parallel_search.
        # parallel_search calls self.crossref.search, etc.
        
        # To avoid threading complexity in unit test, we can patch concurrent.futures.ThreadPoolExecutor
        # OR just test search_works behavior if we mock the executor to run synchronously.
        # Simpler: Patch ReferenceManager.parallel_search to avoid real threading, 
        # but that skips the logic we want to test (aggregation).
        
        # Best approach: Patch the API methods and let ThreadPoolExecutor run (it works with mocks).
        
        with patch('src.api.PubMedAPI.search', return_value=[]), \
             patch('src.api.GoogleBooksAPI.search', return_value=[]):
            
            results = self.manager.search_works("test query")
            
            self.assertTrue(len(results) >= 1)
            self.assertEqual(results[0].title, STD_ARTICLE.title)
            self.assertEqual(results[0].source, "crossref")

    # ------------------------------------------------------------------------
    # 2. Deduplication Behavior
    # ------------------------------------------------------------------------
    def test_deduplication_exact_doi(self):
        """Verify strict DOI deduplication."""
        # Create a duplicate object
        dup = STD_ARTICLE
        # self.manager._deduplicate_results expects a list of Publications
        
        api_results = [STD_ARTICLE, dup]
        unique = self.manager._deduplicate_results(api_results)
        
        self.assertEqual(len(unique), 1)
        self.assertEqual(unique[0].doi, STD_ARTICLE.doi)

    def test_deduplication_fuzzy_title(self):
        """Verify fuzzy title deduplication."""
        # Create a near-duplicate without DOI
        import copy
        orig = copy.copy(STD_ARTICLE)
        orig.doi = "" # Force title check
        
        dup = copy.copy(STD_ARTICLE)
        dup.doi = ""
        dup.title = "A Study of Reference Management." # Trailing dot
        
        api_results = [orig, dup]
        unique = self.manager._deduplicate_results(api_results)
        
        self.assertEqual(len(unique), 1)

    # ------------------------------------------------------------------------
    # 3. Citation Stability
    # ------------------------------------------------------------------------
    def test_citation_std_article(self):
        """Verify standard article citation."""
        from src.referencing.referencing import in_text_citation
        
        # Should be "(Smith & Doe, 2023)" for APA/Harvard-ish
        # referencing.py's in_text_citation logic:
        # if 2 authors: "Family & Family"
        
        # We need to convert Publication object to dict for referencing.py legacy functions?
        # referencing.py functions often expect dicts.
        # Let's check: in_text_citation(ref: Union[Dict, Any]...)
        
        from dataclasses import asdict
        pub_dict = asdict(STD_ARTICLE)
        
        cite = in_text_citation(pub_dict, style="harvard")
        self.assertIn("Smith", cite)
        self.assertIn("Doe", cite)
        self.assertIn("2023", cite)

    def test_citation_missing_date(self):
        """Verify n.d. handling."""
        from src.referencing.referencing import in_text_citation
        from dataclasses import asdict
        
        pub_dict = asdict(MISSING_DATE)
        cite = in_text_citation(pub_dict, style="apa")
        
        self.assertIn("n.d.", cite)

if __name__ == "__main__":
    unittest.main()
