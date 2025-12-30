"""Comprehensive tests for author search edge case fixes."""
import unittest
from unittest.mock import patch, MagicMock


class TestAuthorSearchEdgeCases(unittest.TestCase):
    """Test edge cases in author search: hyphenated names, accents, and typos."""
    
    def setUp(self):
        """Set up mock config for all tests."""
        self.config_patcher = patch('src.reference_manager.Config')
        self.mock_config = self.config_patcher.start()
        self.mock_config.CROSSREF_MAILTO = "test@example.com"
        # Disable Google Books to simplify tests (avoid extra requests)
        self.mock_config.GOOGLE_BOOKS_API_KEY = ""
    
    def tearDown(self):
        """Clean up patches."""
        self.config_patcher.stop()
    
    # ========== FIX #1: HYPHENATED SURNAMES ==========
    
    @patch('src.api.requests.get')
    def test_hyphenated_surname_single_word(self, mock_get):
        """Test searching for hyphenated surname only: 'Smith-Jones'"""
        from src.referencing import referencing
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {
                "items": [{
                    "author": [{"given": "John", "family": "Smith-Jones"}],
                    "title": ["Test Publication"],
                    "type": "article",
                    "published-print": {"date-parts": [[2020]]},
                    "publisher": "Test Publisher",
                    "DOI": "10.1234/test"
                }]
            }
        }
        mock_get.return_value = mock_response
        
        results = referencing.lookup_author_works("Smith-Jones", {})
        
        self.assertEqual(len(results), 1)
        self.assertIn("Smith-Jones", results[0]["authors"][0])
    
    @patch('src.api.requests.get')
    def test_hyphenated_surname_with_first_name(self, mock_get):
        """Test searching 'John Smith-Jones' finds author with hyphenated surname."""
        from src.referencing import referencing
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {
                "items": [{
                    "author": [{"given": "John", "family": "Smith-Jones"}],
                    "title": ["Test Publication"],
                    "type": "article",
                    "published-print": {"date-parts": [[2020]]},
                    "publisher": "Test Publisher",
                    "DOI": "10.1234/test"
                }]
            }
        }
        mock_get.return_value = mock_response
        
        results = referencing.lookup_author_works("John Smith-Jones")
        
        self.assertEqual(len(results), 1)
        self.assertIn("Smith-Jones", results[0]["authors"][0])
    
    # ========== FIX #2: ACCENT NORMALIZATION ==========
    
    @patch('src.api.requests.get')
    def test_accent_in_surname_search_without_accent(self, mock_get):
        """Test searching 'Garcia' finds 'García'."""
        from src.referencing import referencing
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {
                "items": [{
                    "author": [{"given": "José", "family": "García"}],
                    "title": ["Test Publication"],
                    "type": "article",
                    "published-print": {"date-parts": [[2020]]},
                    "publisher": "Test Publisher",
                    "DOI": "10.1234/test"
                }]
            }
        }
        mock_get.return_value = mock_response
        
        # Search without accents
        results = referencing.lookup_author_works("Garcia")
        
        self.assertEqual(len(results), 1)
        self.assertIn("García", results[0]["authors"][0])
    
    @patch('src.api.requests.get')
    def test_accent_in_first_name_search_without_accent(self, mock_get):
        """Test searching 'Jose Garcia' finds 'José García'."""
        from src.referencing import referencing
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {
                "items": [{
                    "author": [{"given": "José", "family": "García"}],
                    "title": ["Test Publication"],
                    "type": "article",
                    "published-print": {"date-parts": [[2020]]},
                    "publisher": "Test Publisher",
                    "DOI": "10.1234/test"
                }]
            }
        }
        mock_get.return_value = mock_response
        
        # Search without accents
        results = referencing.lookup_author_works("Jose Garcia")
        
        self.assertEqual(len(results), 1)
        self.assertIn("García", results[0]["authors"][0])
    
    @patch('src.api.requests.get')
    def test_german_umlaut_normalization(self, mock_get):
        """Test searching 'Muller' finds 'Müller'."""
        from src.referencing import referencing
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {
                "items": [{
                    "author": [{"given": "Hans", "family": "Müller"}],
                    "title": ["Test Publication"],
                    "type": "article",
                    "published-print": {"date-parts": [[2020]]},
                    "publisher": "Test Publisher",
                    "DOI": "10.1234/test"
                }]
            }
        }
        mock_get.return_value = mock_response
        
        results = referencing.lookup_author_works("Muller")
        
        self.assertEqual(len(results), 1)
        self.assertIn("Müller", results[0]["authors"][0])
    
    # ========== FIX #3: FUZZY MATCHING FOR TYPOS ==========
    
    @patch('src.api.requests.get')
    def test_typo_in_surname_christoper_finds_christopher(self, mock_get):
        """Test searching 'Christoper Bishop' (typo) finds 'Christopher Bishop'."""
        from src.referencing import referencing
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {
                "items": [{
                    "author": [{"given": "Christopher", "family": "Bishop"}],
                    "title": ["Pattern Recognition"],
                    "type": "book",
                    "published-print": {"date-parts": [[2006]]},
                    "publisher": "Springer",
                    "DOI": "10.1007/test"
                }]
            }
        }
        mock_get.return_value = mock_response
        
        # Search with typo in first name
        results = referencing.lookup_author_works("Christoper Bishop")
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Pattern Recognition")
    
    @patch('src.api.requests.get')
    def test_typo_in_surname_smyth_finds_smith(self, mock_get):
        """Test searching 'Smyth' (close variant) finds 'Smith'."""
        from src.referencing import referencing
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {
                "items": [{
                    "author": [{"given": "John", "family": "Smith"}],
                    "title": ["Test Publication"],
                    "type": "article",
                    "published-print": {"date-parts": [[2020]]},
                    "publisher": "Test Publisher",
                    "DOI": "10.1234/test"
                }]
            }
        }
        mock_get.return_value = mock_response
        
        # Note: "Smyth" vs "Smith" is 80% similar, below our 85% threshold
        # This should NOT match (different names, not a typo)
        results = referencing.lookup_author_works("Smyth")
        
        # Should not match because similarity is below threshold
        self.assertEqual(len(results), 0)
    
    @patch('src.api.requests.get')
    def test_minor_typo_matches(self, mock_get):
        """Test that minor typos (>85% similar) still match."""
        from src.referencing import referencing
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {
                "items": [{
                    "author": [{"given": "Alexander", "family": "Anderson"}],
                    "title": ["Test Publication"],
                    "type": "article",
                    "published-print": {"date-parts": [[2020]]},
                    "publisher": "Test Publisher",
                    "DOI": "10.1234/test"
                }]
            }
        }
        mock_get.return_value = mock_response
        
        # "Andersen" vs "Anderson" is 88.9% similar (should match)
        results = referencing.lookup_author_works("Andersen")
        
        self.assertEqual(len(results), 1)
        self.assertIn("Anderson", results[0]["authors"][0])
    
    # ========== COMBINED TESTS ==========
    
    @patch('src.api.requests.get')
    def test_combined_accent_and_typo(self, mock_get):
        """Test accent normalization + fuzzy matching together."""
        from src.referencing import referencing
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {
                "items": [{
                    "author": [{"given": "François", "family": "Müller"}],
                    "title": ["Test Publication"],
                    "type": "article",
                    "published-print": {"date-parts": [[2020]]},
                    "publisher": "Test Publisher",
                    "DOI": "10.1234/test"
                }]
            }
        }
        mock_get.return_value = mock_response
        
        # Search with no accents and minor typo: "Francois Muller" (no typo in surname)
        results = referencing.lookup_author_works("Francois Muller")
        
        # Should match: accents normalized
        self.assertEqual(len(results), 1)


if __name__ == '__main__':
    unittest.main()
