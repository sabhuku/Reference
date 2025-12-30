"""Pytest configuration and fixtures."""
import os
import json
from pathlib import Path
from typing import Dict, Any, Generator

import pytest
from unittest.mock import MagicMock, patch

# Add the project root to the Python path
PROJECT_ROOT = Path(__file__).parent.parent
os.environ["PYTHONPATH"] = str(PROJECT_ROOT)

# Sample test data
@pytest.fixture
def sample_publication() -> Dict[str, Any]:
    """Return a sample publication for testing."""
    return {
        "source": "crossref",
        "pub_type": "journal-article",
        "authors": ["Smith, John", "Doe, Jane"],
        "year": "2023",
        "title": "A Sample Publication Title",
        "journal": "Journal of Testing",
        "publisher": "Test Publisher",
        "volume": "12",
        "issue": "3",
        "pages": "123-145",
        "doi": "10.1234/test.2023.456"
    }

@pytest.fixture
def mock_requests_get() -> Generator[MagicMock, None, None]:
    """Mock for requests.get."""
    with patch('requests.get') as mock_get:
        yield mock_get

@pytest.fixture
def mock_cache_file(tmp_path) -> str:
    """Create a temporary cache file for testing."""
    cache_file = tmp_path / "test_cache.json"
    cache_file.write_text("{}")
    return str(cache_file)

@pytest.fixture(autouse=True)
def mock_environment_vars() -> None:
    """Set up test environment variables."""
    os.environ.update({
        "CROSSREF_MAILTO": "test@example.com",
        "GOOGLE_BOOKS_API_KEY": "test-api-key",
        "LOG_LEVEL": "WARNING"
    })
