"""Tests for API utility functions."""
import json
from unittest.mock import patch, MagicMock

import pytest
import requests
from requests.exceptions import RequestException, HTTPError

from referencing.utils.api_utils import (
    APIError,
    handle_api_response,
    safe_crossref_request,
    safe_google_books_request,
)

# Test data
SAMPLE_CROSSREF_RESPONSE = {
    "status": "ok",
    "message-type": "work",
    "message-version": "1.0.0",
    "message": {
        "DOI": "10.1234/test.2023.456",
        "title": ["A Test Publication"],
        "author": [
            {"given": "John", "family": "Doe"},
            {"given": "Jane", "family": "Smith"}
        ],
        "published-print": {"date-parts": [[2023, 1, 1]]},
        "type": "journal-article"
    }
}

SAMPLE_GOOGLE_BOOKS_RESPONSE = {
    "kind": "books#volumes",
    "totalItems": 1,
    "items": [{
        "volumeInfo": {
            "title": "Test Book",
            "authors": ["John Doe"],
            "publishedDate": "2023-01-01",
            "publisher": "Test Publisher"
        }
    }]
}

class TestHandleAPIResponse:
    """Tests for the handle_api_response function."""
    
    def test_handle_valid_response(self):
        """Test handling a valid JSON response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"key": "value"}
        
        result = handle_api_response(mock_response, "Test API")
        assert result == {"key": "value"}
    
    def test_handle_invalid_json(self):
        """Test handling invalid JSON response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)
        
        with pytest.raises(APIError) as excinfo:
            handle_api_response(mock_response, "Test API")
        assert "invalid JSON" in str(excinfo.value)
    
    def test_handle_http_error(self):
        """Test handling HTTP errors."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = HTTPError("Not found")
        
        with pytest.raises(APIError) as excinfo:
            handle_api_response(mock_response, "Test API")
        assert "Test API request failed" in str(excinfo.value)

class TestSafeAPIRequests:
    """Tests for safe API request functions."""
    
    @patch('utils.api_utils.requests.get')
    def test_safe_crossref_request_success(self, mock_get):
        """Test successful Crossref API request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_CROSSREF_RESPONSE
        mock_get.return_value = mock_response
        
        result = safe_crossref_request("https://api.crossref.org/works")
        assert result == SAMPLE_CROSSREF_RESPONSE
    
    @patch('utils.api_utils.requests.get')
    def test_safe_google_books_request_success(self, mock_get):
        """Test successful Google Books API request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_GOOGLE_BOOKS_RESPONSE
        mock_get.return_value = mock_response
        
        result = safe_google_books_request("https://www.googleapis.com/books/v1/volumes")
        assert result == SAMPLE_GOOGLE_BOOKS_RESPONSE
    
    @patch('utils.api_utils.requests.get')
    def test_safe_request_retry_on_failure(self, mock_get):
        """Test that requests are retried on failure."""
        # First request fails, second succeeds
        mock_response1 = MagicMock()
        mock_response1.status_code = 429  # Too Many Requests
        mock_response1.raise_for_status.side_effect = HTTPError("Rate limited")
        
        mock_response2 = MagicMock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = SAMPLE_CROSSREF_RESPONSE
        
        mock_get.side_effect = [mock_response1, mock_response2]
        
        result = safe_crossref_request("https://api.crossref.org/works")
        assert result == SAMPLE_CROSSREF_RESPONSE
        assert mock_get.call_count == 2

class TestAPIError:
    """Tests for the APIError exception class."""
    
    def test_api_error_basic(self):
        """Test basic API error creation."""
        error = APIError("Test error")
        assert str(error) == "Test error"
        assert error.status_code is None
        assert error.response_text is None
    
    def test_api_error_with_status(self):
        """Test API error with status code."""
        error = APIError("Test error", status_code=404)
        assert "404" in str(error)
        assert error.status_code == 404
    
    def test_api_error_with_response_text(self):
        """Test API error with response text."""
        error = APIError("Test error", status_code=500, response_text="Server error")
        assert "Server error" in str(error)
