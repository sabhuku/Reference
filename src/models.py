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
    isbn: str = ""
    match_type: str = "fuzzy"
    confidence_score: float = 0.0
    retrieval_method: str = "api"
    # Normalization & Provenance
    normalized_authors: List[str] = None
    authors_inferred: bool = False
    year_status: str = "present"  # present, explicitly_undated, missing
    source_type_inferred: bool = False
    normalization_log: List[str] = None
    # Specialized Fields for Web/Chapters
    url: str = ""
    access_date: str = ""
    editor: str = ""
    # Harvard Guide Enhancements
    edition: str = ""  # e.g., "4th edn."
    collection: str = ""  # e.g., "Safari Books Online", "ACM Digital Library"
    # Conference Paper Support
    conference_name: str = ""  # e.g., "International Conference on AI"
    conference_location: str = ""  # e.g., "London, UK"
    conference_date: str = ""  # e.g., "15-17 June"

    def __post_init__(self):
        if self.normalized_authors is None:
            self.normalized_authors = []
        if self.normalization_log is None:
            self.normalization_log = []


    @staticmethod
    def escape_bibtex(text: str) -> str:
        """Escape special LaTeX characters for BibTeX."""
        if not text:
            return ""
        
        # Mapping of special characters to their escaped versions
        CHARS_TO_ESCAPE = {
            '&': r'\&',
            '%': r'\%',
            '$': r'\$',
            '#': r'\#',
            '_': r'\_',
            '{': r'\{',
            '}': r'\}',
            '~': r'\textasciitilde{}',
            '^': r'\textasciicircum{}',
            '\\': r'\textbackslash{}',
        }
        
        # Process character by character to avoid re-escaping
        return ''.join(CHARS_TO_ESCAPE.get(char, char) for char in str(text))

    def to_bibtex(self) -> str:
        """Convert to BibTeX format."""
        # Generate a citation key
        if self.authors and self.year and self.title:
            first_author = str(self.authors[0]).split(',')[0].lower()
            first_author = first_author.split()[-1] if ' ' in first_author else first_author
            first_word = self.title.split()[0].lower()
            # Sanitize key: ascii only, no spaces
            import re
            key_base = f"{first_author}{self.year}{first_word}"
            key = re.sub(r'[^a-z0-9]', '', key_base)
        else:
            key = f"ref{hash(str(self)) & 0xFFFFFFFF}"
        
        # Map reference type to BibTeX type
        pub_lower = self.pub_type.lower()
        if 'book' in pub_lower:
            entry_type = 'book'
        elif 'chapter' in pub_lower:
            entry_type = 'inbook'
        elif 'thesis' in pub_lower:
            entry_type = 'phdthesis'
        elif 'report' in pub_lower:
            entry_type = 'techreport'
        elif 'conference' in pub_lower or 'proceedings' in pub_lower:
            entry_type = 'inproceedings'
        else:
            entry_type = 'article'
        
        # Helper to escape
        esc = self.escape_bibtex

        # Build fields
        fields = []
        if self.title:
            fields.append(f"    title = {{{esc(self.title)}}}")
        if self.authors:
            # Authors in src/models.py are List[str] like "Doe, John"
            # BibTeX wants "Doe, John and Smith, Jane"
            # We strictly escape each author string individually
            authors = ' and '.join([esc(a) for a in self.authors])
            fields.append(f"    author = {{{authors}}}")
        if self.year:
            fields.append(f"    year = {{{esc(self.year)}}}")
        if self.journal:
            fields.append(f"    journal = {{{esc(self.journal)}}}")
        if self.volume:
            fields.append(f"    volume = {{{esc(self.volume)}}}")
        if self.issue:
            fields.append(f"    number = {{{esc(self.issue)}}}")
        if self.pages:
            fields.append(f"    pages = {{{esc(self.pages)}}}")
        if self.publisher:
            fields.append(f"    publisher = {{{esc(self.publisher)}}}")
        if self.doi:
            fields.append(f"    doi = {{{esc(self.doi)}}}")
        if self.isbn:
            fields.append(f"    isbn = {{{esc(self.isbn)}}}")
        if self.url:
            fields.append(f"    url = {{{esc(self.url)}}}")
        if self.editor:
            fields.append(f"    editor = {{{esc(self.editor)}}}")
        if self.edition:
            fields.append(f"    edition = {{{esc(self.edition)}}}")
        if self.collection:
            fields.append(f"    note = {{Available from {esc(self.collection)}}}")
        if self.conference_name:
            fields.append(f"    booktitle = {{{esc(self.conference_name)}}}")
        if self.conference_location:
            fields.append(f"    address = {{{esc(self.conference_location)}}}")
        
        # Combine into BibTeX entry
        bibtex = [f"@{entry_type}{{{key},"]
        bibtex.append(",\n".join(fields))
        bibtex.append("}")
        
        return "\n".join(bibtex)
    
    def to_ris(self) -> str:
        """Convert to RIS format."""
        ris = []
        
        # Map reference type to RIS type
        pub_lower = self.pub_type.lower()
        if 'book' in pub_lower:
            entry_type = 'BOOK'
        elif 'chapter' in pub_lower:
            entry_type = 'CHAP'
        elif 'thesis' in pub_lower:
            entry_type = 'THES'
        elif 'report' in pub_lower:
            entry_type = 'RPRT'
        elif 'conference' in pub_lower:
            entry_type = 'CPAPER'
        else:
            entry_type = 'JOUR'
        
        ris.append(f"TY  - {entry_type}")
        
        # Add authors
        for author in self.authors:
            ris.append(f"AU  - {author}")
        
        # Add other fields
        if self.title:
            ris.append(f"TI  - {self.title}")
        if self.journal:
            ris.append(f"JO  - {self.journal}")
        if self.volume:
            ris.append(f"VL  - {self.volume}")
        if self.issue:
            ris.append(f"IS  - {self.issue}")
        if self.pages:
            ris.append(f"SP  - {self.pages}")
        if self.year:
            ris.append(f"PY  - {self.year}")
        if self.doi:
            ris.append(f"DO  - {self.doi}")
        if self.isbn:
            ris.append(f"SN  - {self.isbn}")
        if self.publisher:
            ris.append(f"PB  - {self.publisher}")
        if self.url:
            ris.append(f"UR  - {self.url}")
        if self.access_date:
            ris.append(f"Y2  - {self.access_date}")
        if self.edition:
            ris.append(f"ET  - {self.edition}")
        if self.collection:
            ris.append(f"DB  - {self.collection}")
        if self.conference_name:
            ris.append(f"T2  - {self.conference_name}")
        if self.conference_location:
            ris.append(f"CY  - {self.conference_location}")
        if self.conference_date:
            ris.append(f"Y2  - {self.conference_date}")
        if self.editor:
            ris.append(f"ED  - {self.editor}")
        
        ris.append("ER  - ")
        ris.append("")
        
        return "\n".join(ris)