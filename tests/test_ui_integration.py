import pytest
from unittest.mock import MagicMock
from src.reference_manager import ReferenceManager
from src.models import Publication

class TestUIIntegration:
    def test_compliance_result_structure(self):
        """
        Verify that check_style_compliance returns the 'results' list 
        needed for the updated dashboard template.
        """
        manager = ReferenceManager()
        
        # Create a mock publication
        pub = Publication(
            source="manual",
            pub_type="book",
            authors=["Smith, J."],
            year="2023",
            title="UI Test Book",
            journal="",
            publisher="Test Pub",
            location="London",
            volume="", issue="", pages="", doi=""
        )
        
        # Determine expected behavior
        # It should return dict with 'report', 'feedback', and 'results'
        result = manager.check_style_compliance([pub])
        
        assert "results" in result
        assert isinstance(result["results"], list)
        assert len(result["results"]) == 1
        
        item = result["results"][0]
        assert "display_title" in item
        assert "compliance_score" in item
        assert "violations" in item
        assert "actions" in item
        assert item["display_title"] == "UI Test Book (Smith, J., 2023)"
        # Since it's a book, it might have missing fields or perfect score. 
        # Just check keys exist.
