"""Configuration loader with environment variable support."""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class Config:
    """Application configuration."""
    
    # API Configuration
    CROSSREF_MAILTO: str = os.getenv("CROSSREF_MAILTO", "your.email@example.com")
    GOOGLE_BOOKS_API_KEY: str = os.getenv("GOOGLE_BOOKS_API_KEY", "")
    
    # Application Settings
    DOWNLOAD_FOLDER: str = os.getenv("DOWNLOAD_FOLDER", "downloads")
    CACHE_FILE: str = os.getenv("CACHE_FILE", "cache.json")
    WORD_FILENAME: str = os.getenv("WORD_FILENAME", "references.docx")
    
    # API Endpoints
    CROSSREF_API_URL: str = "https://api.crossref.org/works"
    GOOGLE_BOOKS_API_URL: str = "https://www.googleapis.com/books/v1/volumes"
    
    # Citation Styles
    STYLE_HARVARD: str = "harvard"
    STYLE_APA: str = "apa"
    STYLE_IEEE: str = "ieee"
    DEFAULT_STYLE: str = STYLE_HARVARD
    
    # Name particles for better name parsing
    NAME_PARTICLES = {
        'van', 'de', 'der', 'den', 'van den', 'van der',
        'von', 'zu', 'del', 'della', 'di', 'da', 'dos', 'das', 'do'
    }
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "app.log")
    
    @classmethod
    def ensure_directories_exist(cls) -> None:
        """Ensure required directories exist."""
        os.makedirs(cls.DOWNLOAD_FOLDER, exist_ok=True)
        
    @classmethod
    def get_cache_path(cls) -> str:
        """Get the full path to the cache file."""
        return str(Path(cls.DOWNLOAD_FOLDER) / cls.CACHE_FILE)
    
    @classmethod
    def get_word_path(cls) -> str:
        """Get the full path to the output Word document."""
        return str(Path(cls.DOWNLOAD_FOLDER) / cls.WORD_FILENAME)

# Ensure required directories exist on import
Config.ensure_directories_exist()
