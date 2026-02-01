"""
Stress test for Harvard Compliance Subsystem.
Feeds 'ugly' real-world-style student data into the system.
"""
import pytest
from src.models import Publication
from src.style.reporter import HarvardComplianceReporter
from src.style.remediation import RemediationGenerator

def test_stress_ugly_references():
    """Run compliance check on a list of garbage/ugly references."""
    
    ugly_refs = [
        # 1. The "Lazy Student" - minimal info
        Publication(
            source="manual", pub_type="website", authors=[], year="", title="google",
            journal="", publisher="", location="", volume="", issue="", pages="", doi=""
        ),
        # 2. The "Copy-Paste" - all caps, weird formatting
        Publication(
            source="manual", pub_type="journal-article", 
            authors=["SMITH, J", "doe, a"], # Mixed case conventions
            year="2022", 
            title="IMPACT OF AI ON SOCIETY", # SHOUTING
            journal="science journal", # Lowercase
            publisher="", location="", volume="12", issue="", pages="1-10", doi=""
        ),
        # 3. The "Uncertain" - question marks in year, weird author
        Publication(
            source="manual", pub_type="book", 
            authors=["The Guy from Youtube"], 
            year="2023?", 
            title="some tutorial", 
            journal="", publisher="internet", location="", 
            volume="", issue="", pages="", doi=""
        ),
        # 4. The "Almost Right but Wrong" - missing critical book fields
        Publication(
            source="manual", pub_type="book",
            authors=["Obama, B."],
            year="2020",
            title="A Promised Land",
            journal="",
            publisher="", # Missing publisher
            location="", # Missing city
            volume="", issue="", pages="", doi=""
        ),
        # 5. The "Complete Junk"
        Publication(
            source="manual", pub_type="unknown", authors=[], year="", title="", 
            journal="", publisher="", location="", volume="", issue="", pages="", doi=""
        ),
    ]

    print(f"\n--- Stress Testing with {len(ugly_refs)} UGLY references ---")
    
    # Run Reporter
    reporter = HarvardComplianceReporter()
    report = reporter.generate_report(ugly_refs)
    
    print(f"Overall Score: {report.overall_score}")
    print(f"Marker Summary: {report.marker_summary}")
    print(f"Total Errors: {report.stats.error_count}")
    print(f"Total Warnings: {report.stats.warning_count}")
    
    # Run Remediation
    remediator = RemediationGenerator()
    feedback = remediator.generate(report)
    
    print("\n--- Student Feedback Generated ---")
    for item in feedback.references:
        print(f"\nRef: {item.display_title}")
        for action in item.actions:
            print(f"  [{action.priority}] {action.action}")

    # Assertions to ensure it caught the mess
    assert report.overall_score < 50, "Score should be terrible for this junk"
    assert report.stats.error_count >= 5, "Should have many errors"
    assert any("check if an author" in a.action.lower() for r in feedback.references for a in r.actions)
    assert any("capitalization" in a.action.lower() for r in feedback.references for a in r.actions)

if __name__ == "__main__":
    test_stress_ugly_references()
