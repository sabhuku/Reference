
import unittest
from src.referencing.referencing import validate_publication

class TestSchemaValidation(unittest.TestCase):
    def test_valid_publication(self):
        valid = {
            "title": "Valid Title",
            "authors": ["Author, A."],
            "year": 2023
        }
        is_valid, msg = validate_publication(valid)
        self.assertTrue(is_valid)
        self.assertIsNone(msg)

    def test_missing_title(self):
        invalid = {
            "authors": ["Author, A."],
            "year": 2023
        }
        is_valid, msg = validate_publication(invalid)
        self.assertFalse(is_valid)
        self.assertIn("title", msg)

    def test_empty_title(self):
        invalid = {"title": "   "}
        is_valid, msg = validate_publication(invalid)
        self.assertFalse(is_valid)
        self.assertIn("title", msg)

    def test_invalid_authors_type(self):
        invalid = {
            "title": "Title",
            "authors": 12345 
        }
        is_valid, msg = validate_publication(invalid)
        self.assertFalse(is_valid)
        self.assertIn("authors", msg)

    def test_valid_authors_string(self):
        valid = {
            "title": "Title",
            "authors": "Author, A."
        }
        is_valid, msg = validate_publication(valid)
        self.assertTrue(is_valid)
        
    def test_invalid_year_type(self):
        invalid = {
            "title": "Title",
            "year": [] 
        }
        is_valid, msg = validate_publication(invalid)
        self.assertFalse(is_valid)
        self.assertIn("year", msg)

if __name__ == "__main__":
    unittest.main()
