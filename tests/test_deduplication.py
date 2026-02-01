import unittest
from src.referencing.referencing import get_dedupe_key, is_duplicate

class TestDeduplication(unittest.TestCase):
    def test_get_dedupe_key_with_doi(self):
        ref = {"doi": "10.1001/test", "title": "Different Title"}
        self.assertEqual(get_dedupe_key(ref), "10.1001/test")
        
        ref_case = {"doi": "10.1001/TEST ", "title": "Title"}
        self.assertEqual(get_dedupe_key(ref_case), "10.1001/test")

    def test_get_dedupe_key_without_doi(self):
        ref = {
            "title": "A Great Paper!", 
            "authors": ["Smith, John", "Doe, Jane"], 
            "year": "2023"
        }
        # Normalized title: agreatpaper
        # Author: smith
        # Year: 2023
        self.assertEqual(get_dedupe_key(ref), "agreatpaper|smith|2023")

    def test_get_dedupe_key_normalization(self):
        ref1 = {"title": "Test Paper", "authors": ["Smith, J."], "year": "2020"}
        ref2 = {"title": "  test-paper... ", "authors": "Smith, J.", "year": " 2020"}
        self.assertEqual(get_dedupe_key(ref1), get_dedupe_key(ref2))

    def test_is_duplicate(self):
        existing = [
            {"doi": "10.1111/abc", "title": "Existing One"},
            {"title": "No DOI Paper", "authors": "Jones, A.", "year": "2022"}
        ]
        
        # Exact DOI match
        new_doi = {"doi": "10.1111/ABC", "title": "Something Else"}
        self.assertTrue(is_duplicate(new_doi, existing))
        
        # Soft match
        new_soft = {"title": "No DOI Paper!", "authors": ["Jones, A."], "year": "2022"}
        self.assertTrue(is_duplicate(new_soft, existing))
        
        # No match
        new_diff = {"title": "Different Paper", "authors": "Jones, A.", "year": "2022"}
        self.assertFalse(is_duplicate(new_diff, existing))

if __name__ == "__main__":
    unittest.main()
