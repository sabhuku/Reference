"""Tests for citation formatting functions."""
import pytest

from referencing.referencing import (
    _authors_as_string_harvard,
    _authors_as_string_apa,
    _authors_as_string_ieee,
    in_text_citation,
    reference_entry
)

# Test data
SAMPLE_PUBLICATION = {
    "source": "crossref",
    "pub_type": "journal-article",
    "authors": ["Smith, John", "Doe, Jane", "Johnson, Robert"],
    "year": "2023",
    "title": "A Sample Publication Title",
    "journal": "Journal of Testing",
    "publisher": "Test Publisher",
    "volume": "12",
    "issue": "3",
    "pages": "123-145",
    "doi": "10.1234/test.2023.456"
}

class TestAuthorFormatting:
    """Tests for author name formatting functions."""
    
    def test_harvard_authors_single(self):
        """Test Harvard style with single author."""
        authors = ["Smith, John"]
        assert _authors_as_string_harvard(authors) == "Smith, John"
    
    def test_harvard_authors_two(self):
        """Test Harvard style with two authors."""
        authors = ["Smith, John", "Doe, Jane"]
        assert _authors_as_string_harvard(authors) == "Smith, John and Doe, Jane"
    
    def test_harvard_authors_three(self):
        """Test Harvard style with three authors."""
        authors = ["Smith, John", "Doe, Jane", "Johnson, Robert"]
        assert _authors_as_string_harvard(authors) == "Smith, John, Doe, Jane and Johnson, Robert"
    
    def test_apa_authors_single(self):
        """Test APA style with single author."""
        authors = ["Smith, John"]
        assert _authors_as_string_apa(authors) == "Smith, John"
    
    def test_apa_authors_two(self):
        """Test APA style with two authors."""
        authors = ["Smith, John", "Doe, Jane"]
        assert _authors_as_string_apa(authors) == "Smith, John, & Doe, Jane"
    
    def test_apa_authors_three(self):
        """Test APA style with three authors."""
        authors = ["Smith, John", "Doe, Jane", "Johnson, Robert"]
        assert _authors_as_string_apa(authors) == "Smith, John, Doe, Jane, & Johnson, Robert"
    
    def test_ieee_authors_single(self):
        """Test IEEE style with single author."""
        authors = ["Smith, John"]
        assert _authors_as_string_ieee(authors) == "J. Smith"
    
    def test_ieee_authors_two(self):
        """Test IEEE style with two authors."""
        authors = ["Smith, John", "Doe, Jane"]
        assert _authors_as_string_ieee(authors) == "J. Smith and J. Doe"
    
    def test_ieee_authors_three(self):
        """Test IEEE style with three authors."""
        authors = ["Smith, John", "Doe, Jane", "Johnson, Robert"]
        assert _authors_as_string_ieee(authors) == "J. Smith, J. Doe, and R. Johnson"

class TestInTextCitation:
    """Tests for in-text citation formatting."""
    
    def test_harvard_single_author(self):
        """Test Harvard style with single author."""
        meta = {"authors": ["Smith, John"], "year": "2023"}
        assert in_text_citation(meta, "harvard") == "(Smith, 2023)"
    
    def test_harvard_two_authors(self):
        """Test Harvard style with two authors."""
        meta = {"authors": ["Smith, John", "Doe, Jane"], "year": "2023"}
        assert in_text_citation(meta, "harvard") == "(Smith and Doe, 2023)"
    
    def test_harvard_three_authors(self):
        """Test Harvard style with three authors (should use et al.)."""
        meta = {"authors": ["Smith, John", "Doe, Jane", "Johnson, Robert"], "year": "2023"}
        assert in_text_citation(meta, "harvard") == "(Smith et al., 2023)"
    
    def test_ieee_citation(self):
        """Test IEEE style citation (numeric)."""
        meta = {"authors": ["Smith, John"], "year": "2023"}
        assert in_text_citation(meta, "ieee", 1) == "[1]"

class TestReferenceEntry:
    """Tests for full reference entry formatting."""
    
    def test_harvard_journal_article(self):
        """Test Harvard style journal article reference."""
        result = reference_entry(SAMPLE_PUBLICATION, "harvard")
        assert "Smith, John, Doe, Jane and Johnson, Robert (2023) 'A Sample Publication Title'," in result
        assert "Journal of Testing, 12(3), pp. 123-145." in result
        assert "doi:10.1234/test.2023.456" in result
    
    def test_apa_journal_article(self):
        """Test APA style journal article reference."""
        result = reference_entry(SAMPLE_PUBLICATION, "apa")
        assert "Smith, J., Doe, J., & Johnson, R. (2023). A Sample Publication Title. " in result
        assert "Journal of Testing, 12(3), 123-145. " in result
        assert "https://doi.org/10.1234/test.2023.456" in result
    
    def test_ieee_journal_article(self):
        """Test IEEE style journal article reference."""
        result = reference_entry(SAMPLE_PUBLICATION, "ieee", 1)
        assert "J. Smith, J. Doe, and R. Johnson, " in result
        assert "A Sample Publication Title," in result
        assert "Journal of Testing, vol. 12, no. 3, pp. 123-145, 2023." in result
        assert "doi: 10.1234/test.2023.456" in result

    def test_unknown_style(self):
        """Test that an unknown style falls back to Harvard."""
        result = reference_entry(SAMPLE_PUBLICATION, "unknown_style")
        # Should still contain basic publication info
        assert "Smith, John" in result
        assert "A Sample Publication Title" in result
        assert "2023" in result
