"""Integration tests for the Reference Manager workflow."""
import json
from unittest.mock import patch, MagicMock
from pathlib import Path
import pytest

from referencing.reference_manager import ReferenceManager
from referencing.models import Publication

# Sample data for mocking API responses
SAMPLE_DOI = "10.1038/nature12373"
SAMPLE_CROSSREF_RESPONSE = {
    "status": "ok",
    "message-type": "work",
    "message-version": "1.0.0",
    "message": {
        "DOI": SAMPLE_DOI,
        "title": ["Test Title"],
        "author": [{"given": "John", "family": "Doe"}],
        "published": {"date-parts": [[2023, 1, 1]]},
        "type": "journal-article",
        "container-title": ["Nature"],
        "volume": "1",
        "issue": "1",
        "page": "1-10"
    }
}

@pytest.fixture
def mock_requests():
    """Mock requests.get for API calls."""
    with patch('requests.get') as mock_get:
        yield mock_get

@pytest.fixture
def reference_manager(tmp_path):
    """Create a ReferenceManager instance with a temporary cache file."""
    # Create a temporary cache file
    cache_file = tmp_path / "test_cache.json"
    
    # Create a test config
    class TestConfig:
        CACHE_FILE = str(cache_file)
        DEFAULT_STYLE = "apa"
        CROSSREF_MAILTO = "test@example.com"
        GOOGLE_BOOKS_API_KEY = "test_key"
    
    # Patch the config
    with patch('referencing.reference_manager.Config', TestConfig):
        yield ReferenceManager()

class TestReferenceManagerIntegration:
    def test_search_and_cache_workflow(self, reference_manager, mock_requests, tmp_path):
        """Test the complete workflow: search -> cache -> retrieve from cache."""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_CROSSREF_RESPONSE
        mock_response.status_code = 200
        mock_requests.return_value = mock_response
        
        # Step 1: Search for a work (should make an API call)
        result = reference_manager.search_single_work(SAMPLE_DOI)
        
        # Verify the result
        assert result is not None
        assert result.doi == SAMPLE_DOI
        assert result.title == "Test Title"
        
        # Verify the cache was updated
        cache_file = Path(reference_manager.config.CACHE_FILE)
        assert cache_file.exists()
        
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        assert f"query:{SAMPLE_DOI}" in cache_data
        
        # Step 2: Search again (should use cache, no API call)
        mock_requests.reset_mock()
        cached_result = reference_manager.search_single_work(SAMPLE_DOI)
        
        # Verify we got the same result
        assert cached_result.dict() == result.dict()
        
        # Verify no API call was made
        mock_requests.assert_not_called()
    
    def test_export_formats(self, reference_manager, mock_requests, tmp_path):
        """Test exporting references to different formats."""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_CROSSREF_RESPONSE
        mock_response.status_code = 200
        mock_requests.return_value = mock_response
        
        # Add a reference
        reference_manager.search_single_work(SAMPLE_DOI)
        
        # Test BibTeX export
        bibtex = reference_manager.export_bibtex()
        assert "@article" in bibtex
        assert SAMPLE_DOI in bibtex
        
        # Test RIS export
        ris = reference_manager.export_ris()
        assert "TY  - JOUR" in ris
        assert "DO  - " + SAMPLE_DOI in ris

    def test_author_search(self, reference_manager, mock_requests):
        """Test searching for works by author."""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "ok",
            "message-type": "work-list",
            "message-version": "1.0.0",
            "message": {
                "items": [SAMPLE_CROSSREF_RESPONSE["message"]]
            }
        }
        mock_response.status_code = 200
        mock_requests.return_value = mock_response
        
        # Search by author
        results = reference_manager.search_author_works("John Doe")
        
        # Verify results
        assert len(results) > 0
        assert any(r.doi == SAMPLE_DOI for r in results)
