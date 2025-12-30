import unittest
from unittest.mock import patch, MagicMock
import json
from referencing import (
    normalize_simple,
    extract_year,
    looks_like_initial,
    guess_first_last_from_author_query,
    names_match
)

class TestReferencing(unittest.TestCase):
    def test_normalize_simple(self):
        self.assertEqual(normalize_simple("Hello, World!"), "hello world")
        self.assertEqual(normalize_simple("Test-Case"), "testcase")
        self.assertEqual(normalize_simple(" Spaces "), "spaces")
    
    def test_extract_year(self):
        item = {"published-print": {"date-parts": [[2023]]}}
        self.assertEqual(extract_year(item), "2023")
        self.assertEqual(extract_year({}), "n.d.")
    
    def test_looks_like_initial(self):
        self.assertTrue(looks_like_initial("A"))
        self.assertTrue(looks_like_initial("A."))
        self.assertFalse(looks_like_initial("Ab"))
        self.assertFalse(looks_like_initial(""))
    
    def test_guess_first_last_from_author_query(self):
        self.assertEqual(
            guess_first_last_from_author_query("John Smith"),
            ("John", "Smith")
        )
        self.assertEqual(
            guess_first_last_from_author_query("van der Waals"),
            ("", "van der Waals")
        )
    
    def test_names_match(self):
        self.assertTrue(names_match("John", "Smith", "John", "Smith"))
        self.assertTrue(names_match("J", "Smith", "John", "Smith"))
        self.assertFalse(names_match("John", "Smith", "Jane", "Smith"))

if __name__ == '__main__':
    unittest.main()