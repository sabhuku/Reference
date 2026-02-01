
import unittest
from src.models import Publication
from src.normalizer import ReferenceNormalizer
from src.style.harvard_checker import HarvardStyleChecker
from src.style.reporter import HarvardComplianceReporter

class TestParity(unittest.TestCase):
    def setUp(self):
        self.reporter = HarvardComplianceReporter()

    def test_author_normalization_parity(self):
        """Test that different author formats normalize to the same standard."""
        # Case 1: JSON style list of "Surname, Given"
        p1 = Publication(
            source="json", pub_type="journal-article",
            authors=["Smith, John", "Doe, Jane"],
            year="2023", title="A Study", journal="J. Test", volume="1", issue="1", pages="1-10", doi="10.1000/1", publisher="", location=""
        )
        # Case 2: Free text "Given Surname"
        p2 = Publication(
            source="ris", pub_type="journal-article",
            authors=["John Smith", "Jane Doe"],
            year="2023", title="A Study", journal="J. Test", volume="1", issue="1", pages="1-10", doi="10.1000/1", publisher="", location=""
        )
        
        ReferenceNormalizer.normalize(p1)
        ReferenceNormalizer.normalize(p2)
        
        self.assertEqual(p1.normalized_authors, ["Smith, J.", "Doe, J."])
        self.assertEqual(p2.normalized_authors, ["Smith, J.", "Doe, J."])
        self.assertEqual(p1.normalized_authors, p2.normalized_authors)

    def test_compliance_parity(self):
        """Test that equivalent inputs yield identical compliance reports and perfect scores."""
        # Perfect Article
        p1 = Publication(
            source="json", pub_type="journal-article",
            authors=["Smith, John"],
            year="2023", title="Perfect Article", journal="Journal of Testing", 
            volume="10", issue="2", pages="100-110", doi="10.1000/xyz",
            publisher="", location="" # Not needed for article
        )
        
        # Perfect Article from RIS (simulated)
        p2 = Publication(
            source="ris", pub_type="journal-article",
            authors=["John Smith"], # messy input
            year="2023", title="Perfect Article", journal="Journal of Testing",
            volume="10", issue="2", pages="100-110", doi="10.1000/xyz",
            publisher="", location=""
        )
        
        report1 = self.reporter.generate_report([p1])
        report2 = self.reporter.generate_report([p2])
        
        # Verify scores
        self.assertEqual(report1.overall_compliance_score, 100.0)
        self.assertEqual(report2.overall_compliance_score, 100.0)
        
        # Verify normalization logs exists but didn't hurt score
        self.assertTrue(len(report2.details[0].violations) > 0) # Should have info log for author inference
        # Check explicit severity
        severities = [v.severity for v in report2.details[0].violations]
        self.assertNotIn("error", severities)
        self.assertNotIn("warning", severities)
        self.assertIn("info", severities)

    def test_undated_parity(self):
        """Test that explicit 'n.d.' is handled correctly and scores 100%."""
        p = Publication(
            source="ris", pub_type="book",
            authors=["Smith, J."],
            year="n.d.", title="Ancient Text", journal="", volume="", issue="", pages="", doi="",
            publisher="Old Press", location="London"
        )
        
        report = self.reporter.generate_report([p])
        
        self.assertEqual(p.year_status, "explicitly_undated")
        self.assertEqual(p.year, "n.d.")
        self.assertEqual(report.overall_compliance_score, 100.0)

if __name__ == "__main__":
    unittest.main()
