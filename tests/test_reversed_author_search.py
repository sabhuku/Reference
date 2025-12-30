"""Test for reversed author name search fix."""
import unittest
from unittest.mock import patch, MagicMock

class TestReversedAuthorSearch(unittest.TestCase):
    @patch('src.api.requests.get')
    @patch('src.reference_manager.Config')
    def test_bishop_christopher_finds_christopher_bishop(self, mock_config, mock_get):
        """Test that 'Bishop Christopher' finds works by 'Christopher Bishop'."""
        from src.referencing import referencing
        
        # Mock config
        mock_config.CROSSREF_MAILTO = "test@example.com"
        mock_config.GOOGLE_BOOKS_API_KEY = ""
        
        # Mock API response with Christopher Bishop as author
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {
                "items": [{
                    "author": [{"given": "Christopher", "family": "Bishop"}],
                    "title": ["Pattern Recognition and Machine Learning"],
                    "type": "book",
                    "published-print": {"date-parts": [[2006]]},
                    "publisher": "Springer",
                    "DOI": "10.1007/978-0-387-45528-0"
                }]
            }
        }
        mock_get.return_value = mock_response
        
        # Search with reversed name
        results = referencing.lookup_author_works("Bishop Christopher")
        
        # Should find the result
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Pattern Recognition and Machine Learning")
        self.assertIn("Bishop", results[0]["authors"][0])

if __name__ == '__main__':
    unittest.main()
