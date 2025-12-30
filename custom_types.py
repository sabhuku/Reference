from typing import TypedDict, List, Optional

class Author(TypedDict):
    given: str
    family: str

class Publication(TypedDict):
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

class CrossRefResponse(TypedDict):
    message: dict
    items: List[dict]

class CacheDict(TypedDict):
    pass  # This will store both query and author cache entries