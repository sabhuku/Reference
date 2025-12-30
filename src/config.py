"""Configuration settings."""
import os
from dataclasses import dataclass
from typing import Final

@dataclass
class Config:
    """Configuration settings for the reference manager."""
    
    # File paths
    DOWNLOAD_FOLDER: Final[str] = os.getcwd()
    CACHE_FILE: Final[str] = "cache.json"
    WORD_FILENAME: Final[str] = "references.docx"
    
    # API Configuration
    CROSSREF_MAILTO: Final[str] = os.getenv("CROSSREF_MAILTO", "user@example.com")
    GOOGLE_BOOKS_API_KEY: Final[str] = os.getenv("GOOGLE_BOOKS_API_KEY", "")
    
    # API URLs
    CROSSREF_API_URL: Final[str] = "https://api.crossref.org/works"
    GOOGLE_BOOKS_API_URL: Final[str] = "https://www.googleapis.com/books/v1/volumes"
    
    # Reference Styles
    STYLE_HARVARD: Final[str] = "harvard"
    STYLE_APA: Final[str] = "apa"
    STYLE_IEEE: Final[str] = "ieee"
    DEFAULT_STYLE: Final[str] = STYLE_HARVARD
    
    # Name particles for surname parsing
    # Name particles for surname parsing (moved to module-level constant due to dataclass
    # mutable-default restrictions)

# Module-level constant for surname particles (used elsewhere by parsing logic)
NAME_PARTICLES: Final[set[str]] = {
    "van", "von", "der", "den", "ter", "ten",
    "de", "del", "della", "di", "da", "dos", "du",
    "la", "le", "lo", "las", "los"
}