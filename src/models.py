"""Data models for the reference manager."""
from dataclasses import dataclass
from typing import List

@dataclass
class Publication:
    """Represents a publication (article, book, etc.)."""
    source: str
    pub_type: str
    authors: List[str]
    year: str
    title: str
    journal: str
    publisher: str
    location: str
    volume: str
    issue: str
    pages: str
    doi: str