"""Tests for style validation."""
import pytest
from src.style.harvard_checker import HarvardStyleChecker
from src.style.reporter import HarvardComplianceReporter
from src.models import Publication
from src.style.models import Violation, Severity

class TestHarvardStyleChecker:
    
    def test_pass_valid_publication(self):
        """Test a perfectly valid publication."""
        pub = Publication(
            source="test",
            pub_type="journal-article",
            authors=["Smith, J.", "Doe, A."],
            year="2023",
            title="A Valid Title",
            journal="Journal of Testing",
            publisher="",
            location="",
            volume="1",
            issue="2",
            pages="10-20",
            doi="10.1234/5678"
        )
        checker = HarvardStyleChecker()
        violations = checker.check_single(pub)
        assert len(violations) == 0

    def test_missing_author(self):
        """Test missing author error."""
        pub = Publication(
            source="test",
            pub_type="book",
            authors=[], # Empty
            year="2023",
            title="No Author Book",
            journal="",
            publisher="Press",
            location="London",
            volume="",
            issue="",
            pages="",
            doi=""
        )
        checker = HarvardStyleChecker()
        violations = checker.check_single(pub)
        ids = [v.rule_id for v in violations]
        assert "HARVARD.AUTHOR.MISSING" in ids
        
    def test_author_format_warning(self):
        """Test author format warning."""
        pub = Publication(
            source="test",
            pub_type="book",
            authors=["John Smith"], # Wrong format
            year="2023",
            title="Book Title",
            journal="",
            publisher="Press",
            location="City",
            volume="",
            issue="",
            pages="",
            doi=""
        )
        checker = HarvardStyleChecker()
        violations = checker.check_single(pub)
        ids = [v.rule_id for v in violations]
        assert "HARVARD.AUTHOR.FORMAT" in ids

    def test_title_caps(self):
        """Test title capitalization warning."""
        pub = Publication(
            source="test",
            pub_type="article",
            authors=["Smith, J."],
            year="2023",
            title="ALL CAPS TITLE",
            journal="Journal",
            publisher="",
            location="",
            volume="1",
            issue="1",
            pages="1",
            doi="10.1"
        )
        checker = HarvardStyleChecker()
        violations = checker.check_single(pub)
        ids = [v.rule_id for v in violations]
        assert "HARVARD.TITLE.CAPITALIZATION" in ids

    def test_book_location_publisher(self):
        """Test book specific rules."""
        pub = Publication(
            source="test",
            pub_type="book",
            authors=["Smith, J."],
            year="2023",
            title="Book Title",
            journal="",
            publisher="", # Missing
            location="", # Missing
            volume="",
            issue="",
            pages="",
            doi=""
        )
        checker = HarvardStyleChecker()
        violations = checker.check_single(pub)
        ids = [v.rule_id for v in violations]
        assert "HARVARD.BOOK.PUBLISHER_MISSING" in ids
        assert "HARVARD.BOOK.LOCATION_MISSING" in ids
        
    def test_journal_details(self):
        """Test journal details missing."""
        pub = Publication(
            source="test",
            pub_type="journal-article",
            authors=["Smith, J."],
            year="2023",
            title="Article Title",
            journal="Journal",
            publisher="",
            location="",
            volume="", # Missing
            issue="", 
            pages="", # Missing
            doi="10.1"
        )
        checker = HarvardStyleChecker()
        violations = checker.check_single(pub)
        ids = [v.rule_id for v in violations]
        assert "HARVARD.JOURNAL.DETAILS_MISSING" in ids


class TestHarvardComplianceReportGenerator:
    """Test pure logic report generation."""
    
    def test_generate_pure_report(self):
        """Test generator with manually constructed inputs."""
        from src.style.report_generator import HarvardComplianceReportGenerator, ReferenceMetadata
        
        # Inputs
        meta = [
            ReferenceMetadata(id="ref1", display_title="Title 1"),
            ReferenceMetadata(id="ref2", display_title="Title 2")
        ]
        
        violations = [
            Violation("RULE1", "error", "Msg1", "field", "ref1"),
            Violation("RULE2", "warning", "Msg2", "field", "ref2")
        ]
        
        gen = HarvardComplianceReportGenerator()
        report = gen.generate(meta, violations)
        
        assert report.overall_score < 100
        assert report.stats.error_count == 1
        assert report.stats.warning_count == 1
        assert len(report.details) == 2
        assert report.details[0].reference_key == "ref1"
        assert report.details[0].violations[0].rule_id == "RULE1"


class TestRemediationGenerator:
    """Test student remediation generation."""
    
    def test_generate_feedback(self):
        """Test generating feedback from a compliance report."""
        from src.style.remediation import RemediationGenerator
        from src.style.models import ComplianceReport, ReferenceCompliance, Violation, ComplianceStats
        
        # Mock Report
        v1 = Violation("HARVARD.AUTHOR.MISSING", "error", "Missing auth")
        v2 = Violation("HARVARD.DOI_OR_URL.MISSING", "info", "Missing DOI")
        
        ref = ReferenceCompliance(
            reference_key="Ref1",
            display_title="Untitled (2023)",
            violations=[v1, v2]
        )
        
        report = ComplianceReport(
            overall_score=50,
            marker_summary="Summary",
            stats=ComplianceStats(),
            details=[ref]
        )
        
        gen = RemediationGenerator()
        feedback = gen.generate(report)
        
        assert len(feedback.references) == 1
        actions = feedback.references[0].actions
        assert len(actions) == 2
        
        # Check ordering (High priority first)
        assert actions[0].priority == "High"
        assert "check if an author" in actions[0].action.lower()
        
        assert actions[1].priority == "Low"
        assert "consider adding a doi" in actions[1].action.lower()


