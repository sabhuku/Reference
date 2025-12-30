
import unittest
from unittest.mock import MagicMock, patch
from src.reference_manager import ReferenceManager
from src.models import Publication

class TestCombinedAuthorSearch(unittest.TestCase):
    def setUp(self):
        self.manager = ReferenceManager()
        # Mock APIs
        self.manager.crossref = MagicMock()
        self.manager.google_books = MagicMock()
        self.manager.cache = {} # Ensure cache doesn't hit

    def test_search_author_combines_results(self):
        # Setup mock returns
        pub1 = Publication(source="crossref", pub_type="article", authors=["Author"], year="2023", title="Paper 1", journal="Journal", publisher="", location="", volume="", issue="", pages="", doi="")
        pub2 = Publication(source="google_books", pub_type="book", authors=["Author"], year="2022", title="Book 1", journal="", publisher="Publisher", location="", volume="", issue="", pages="", doi="")
        
        self.manager.crossref.search_author.return_value = [pub1]
        self.manager.google_books.search_author.return_value = [pub2]
        
        # Execute
        results = self.manager.search_author_works("Test Author")
        
        # Verify
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], pub1)
        self.assertEqual(results[1], pub2)
        
        # Verify calls
        self.manager.crossref.search_author.assert_called_with("Test Author")
        self.manager.google_books.search_author.assert_called_with("Test Author")

class TestReferencingLookupAuthor(unittest.TestCase):
    @patch('src.referencing.referencing._get_manager')
    def test_lookup_author_works_combines(self, mock_get_manager):
        from src.referencing import referencing
        
        # Setup mock manager
        mock_manager = MagicMock()
        mock_manager.cache = {}
        mock_get_manager.return_value = mock_manager
        
        # Setup mock returns (List[Publication])
        pub1 = Publication(source="crossref", pub_type="article", authors=["Author"], year="2023", title="Paper 1", journal="Journal", publisher="", location="", volume="", issue="", pages="", doi="")
        pub2 = Publication(source="google_books", pub_type="book", authors=["Author"], year="2022", title="Book 1", journal="", publisher="Publisher", location="", volume="", issue="", pages="", doi="")
        
        mock_manager.search_author_works.return_value = [pub1, pub2]
        
        # Execute
        results = referencing.lookup_author_works("Test Author", {})
        
        # Verify
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["source"], "crossref")
        self.assertEqual(results[0]["title"], "Paper 1")
        self.assertEqual(results[1]["source"], "google_books")
        self.assertEqual(results[1]["title"], "Book 1")
        
        mock_manager.search_author_works.assert_called_with("Test Author")

if __name__ == '__main__':
    unittest.main()
