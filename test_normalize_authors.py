import unittest

# import the helper from the Flask UI module
from ui.app import normalize_authors

class TestNormalizeAuthors(unittest.TestCase):
    def test_comma_family_given(self):
        self.assertEqual(normalize_authors("Smith, John"), ["Smith, John"])

    def test_given_family(self):
        self.assertEqual(normalize_authors("John Smith"), ["Smith, John"])

    def test_initials_semicolon(self):
        self.assertEqual(normalize_authors("Smith J.; Doe A."), ["Smith, J.", "Doe, A."])

    def test_comma_pairs(self):
        self.assertEqual(normalize_authors("Smith, J., Doe, A."), ["Smith, J.", "Doe, A."])

    def test_and_separated(self):
        self.assertEqual(normalize_authors("John Smith and Mary Jones"), ["Smith, John", "Jones, Mary"])

    def test_complex(self):
        self.assertEqual(normalize_authors("John A. Smith, Mary B. Jones"), ["Smith, John A.", "Jones, Mary B."])

    def test_particles(self):
        self.assertEqual(normalize_authors("John van der Waals"), ["van der Waals, John"])

    def test_suffix(self):
        self.assertEqual(normalize_authors("John Smith Jr."), ["Smith Jr., John"]) 

    def test_apostrophe(self):
        self.assertEqual(normalize_authors("Tara O'Neil"), ["O'Neil, Tara"]) 

    def test_comma_with_suffix(self):
        self.assertEqual(normalize_authors("Smith Jr., John"), ["Smith Jr., John"]) 

if __name__ == '__main__':
    unittest.main()
