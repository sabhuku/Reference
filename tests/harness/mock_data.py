from src.referencing.models import Reference as Publication

# 1. Standard Article
STD_ARTICLE = Publication(
    id="std-123",
    source="crossref",
    pub_type="journal-article",
    authors=["Smith, John", "Doe, Jane"],
    year="2023",
    title="A Study of Reference Management",
    journal="Journal of Library Science",
    volume="12",
    issue="4",
    pages="100-110",
    doi="10.1000/123456"
)

# 2. Ambiguous Authors (Missing First Names)
AMBIGUOUS_AUTHORS = Publication(
    id="amb-456",
    source="pubmed",
    pub_type="journal-article",
    authors=["Smith J", "Doe J"],
    year="2022",
    title="Ambiguity in Citations",
    doi="10.1000/ambiguous"
)

# 3. Missing Date
MISSING_DATE = Publication(
    id="miss-789",
    source="google_books",
    pub_type="book",
    authors=["Brown, Charlie"],
    year="n.d.",
    title="The Timeless Book",
    publisher="Peanuts Press",
    doi=""
)

# 4. Dictionary Format (Simulating raw API response/cache)
DICT_FORMAT_PUB = {
    "source": "manual",
    "pub_type": "webpage",
    "authors": ["Webmaster, A."],
    "year": "2024",
    "title": "Online Resource",
    "url": "https://example.com"
}
