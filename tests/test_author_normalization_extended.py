
import unittest
from ui.app import normalize_authors

class TestExtendedAuthorNormalization(unittest.TestCase):
    def test_legacy_mode(self):
        # Should return list, just like before
        res = normalize_authors("Smith, John")
        self.assertIsInstance(res, list)
        self.assertEqual(res, ["Smith, John"])
        
        res = normalize_authors("Smith, John; Doe, Jane")
        self.assertEqual(res, ["Smith, John", "Doe, Jane"])

    def test_metadata_mode_semicolon(self):
        res = normalize_authors("Smith, John; Doe, Jane", return_metadata=True)
        self.assertIsInstance(res, dict)
        self.assertEqual(res["authors"], ["Smith, John", "Doe, Jane"])
        self.assertEqual(res["parsing_method"], "semicolon")
        self.assertEqual(res["confidence"], 0.9)
        self.assertFalse(res["ambiguous"])

    def test_metadata_mode_comma_pairs(self):
        # High confidence pairing: "Surname, Given, Surname, Given"
        res = normalize_authors("Smith, John, Doe, Jane", return_metadata=True)
        self.assertEqual(res["authors"], ["Smith, John", "Doe, Jane"])
        self.assertEqual(res["parsing_method"], "comma_pairs")
        self.assertEqual(res["confidence"], 0.8)

    def test_metadata_mode_comma_fallback(self):
        # Ambiguous case: "Smith, Doe" (Could be "Smith, Doe" or "Smith" and "Doe")
        # Current logic treats "Smith, Doe" as two authors if no spaces, or 
        # "Smith, Doe" as one author formatted as "Surname, Given"
        
        # Let's test a case that hits fallback
        # "Smith, Doe, Jones" -> 3 tokens. 
        res = normalize_authors("Smith, Doe, Jones", return_metadata=True)
        self.assertEqual(res["authors"], ["Smith", "Doe", "Jones"]) # formatted by fmt() effectively
        self.assertEqual(res["parsing_method"], "comma_fallback")
        self.assertTrue(res["ambiguous"])
        self.assertEqual(res["confidence"], 0.4)

    def test_metadata_mode_and(self):
        res = normalize_authors("John Smith and Jane Doe", return_metadata=True)
        self.assertEqual(res["authors"], ["Smith, John", "Doe, Jane"])
        self.assertEqual(res["parsing_method"], "and_keyword")
        self.assertEqual(res["confidence"], 0.9)

if __name__ == "__main__":
    unittest.main()
