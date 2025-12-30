import os
from typing import Final

# File paths
DOWNLOAD_FOLDER: Final[str] = os.getcwd()
# For Android Downloads, uncomment this:
# DOWNLOAD_FOLDER = "/storage/emulated/0/Download"

CACHE_FILE: Final[str] = "cache.json"
WORD_FILENAME: Final[str] = "references.docx"

# API Configuration
CROSSREF_MAILTO: Final[str] = "stenford41@hotmail.com"  # Your email
GOOGLE_BOOKS_API_KEY: Final[str] = os.getenv("GOOGLE_BOOKS_API_KEY", "")  # Set this in environment variable

# Reference Styles
STYLE_HARVARD: Final[str] = "harvard"
STYLE_APA: Final[str] = "apa"
STYLE_IEEE: Final[str] = "ieee"
DEFAULT_STYLE: Final[str] = STYLE_HARVARD

# API URLs
CROSSREF_API_URL: Final[str] = "https://api.crossref.org/works"
GOOGLE_BOOKS_API_URL: Final[str] = "https://www.googleapis.com/books/v1/volumes"


# Name particles for surname parsing
NAME_PARTICLES: Final[set[str]] = {
    "van", "von", "der", "den", "ter", "ten",
    "de", "del", "della", "di", "da", "dos", "du",
    "la", "le", "lo", "las", "los"
}