"""Reference data models and utilities."""
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

@dataclass
class Author:
    """Author information."""
    given: str
    family: str
    affiliation: List[str] = field(default_factory=list)
    orcid: Optional[str] = None
    
    def __str__(self):
        return f"{self.family}, {self.given}"

@dataclass
class Reference:
    """A reference to a scholarly work."""
    # Core identifiers
    id: str  # Unique identifier
    doi: Optional[str] = None
    url: Optional[str] = None
    
    # Basic metadata
    title: str = ""
    abstract: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    language: str = "en"
    
    # Authors and contributors
    authors: List[Author] = field(default_factory=list)
    editors: List[Author] = field(default_factory=list)
    
    # Publication info
    pub_type: str = "article"  # article, book, chapter, etc.
    journal: Optional[str] = None
    book_title: Optional[str] = None
    publisher: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    edition: Optional[str] = None
    
    # Dates
    year: Optional[int] = None
    month: Optional[int] = None
    day: Optional[int] = None
    accessed: Optional[datetime] = None
    
    # Additional metadata
    isbn: Optional[str] = None
    issn: Optional[str] = None
    pmid: Optional[str] = None  # PubMed ID
    arxiv_id: Optional[str] = None
    
    # Source and version info
    source: Optional[str] = None  # crossref, semantic_scholar, manual, etc.
    version: str = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for JSON serialization."""
        data = asdict(self)
        
        # Convert datetime to ISO format
        if data['accessed']:
            data['accessed'] = data['accessed'].isoformat()
            
        # Remove None values
        return {k: v for k, v in data.items() if v is not None}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Reference':
        """Create a Reference from a dictionary."""
        # Handle datetime conversion
        if 'accessed' in data and isinstance(data['accessed'], str):
            data['accessed'] = datetime.fromisoformat(data['accessed'])
            
        # Handle author objects
        if 'authors' in data and data['authors'] and isinstance(data['authors'][0], dict):
            data['authors'] = [Author(**a) for a in data['authors']]
            
        if 'editors' in data and data['editors'] and isinstance(data['editors'][0], dict):
            data['editors'] = [Author(**e) for e in data['editors']]
            
        return cls(**data)
    
    def format_citation(self, style: str = 'apa') -> str:
        """Format the reference in the specified citation style."""
        # This is a simplified version - in a real app, you'd use a citation formatter like citeproc-py
        if style.lower() == 'apa':
            return self._format_apa()
        elif style.lower() == 'mla':
            return self._format_mla()
        elif style.lower() == 'chicago':
            return self._format_chicago()
        else:  # Default to APA
            return self._format_apa()
    
    def _format_apa(self) -> str:
        """Format in APA style."""
        parts = []
        
        # Authors
        if self.authors:
            if len(self.authors) == 1:
                parts.append(f"{self.authors[0]}")
            elif len(self.authors) == 2:
                parts.append(f"{self.authors[0]} & {self.authors[1]}")
            else:
                parts.append(", ".join(str(a) for a in self.authors[:-1]) + f", & {self.authors[-1]}")
        
        # Year in parentheses
        if self.year:
            parts[-1] += f" ({self.year})."
        else:
            parts[-1] += "."
        
        # Title
        if self.title:
            parts.append(f" {self.title}.")
        
        # Journal/Book title
        if self.journal:
            parts.append(f" {self.journal},")
            if self.volume:
                parts.append(f" {self.volume}")
                if self.issue:
                    parts.append(f"({self.issue})")
                parts.append(",")
            if self.pages:
                parts.append(f" {self.pages}.")
        
        # Clean up and join
        citation = ' '.join(parts).replace(' .', '.').replace(' ,', ',').strip()
        return citation
    
    def _format_mla(self) -> str:
        """Format in MLA style."""
        parts = []
        
        # Authors
        if self.authors:
            if len(self.authors) == 1:
                parts.append(f"{self.authors[0]}.")
            elif len(self.authors) == 2:
                parts.append(f"{self.authors[0]} and {self.authors[1]}.")
            else:
                parts.append(", ".join(str(a) for a in self.authors[:-1]) + f", and {self.authors[-1]}.")
        
        # Title
        if self.title:
            parts.append(f' "{self.title}."')
        
        # Container
        container = []
        if self.journal:
            container.append(self.journal)
        if self.volume:
            container.append(f"vol. {self.volume}")
        if self.issue:
            container.append(f"no. {self.issue}")
        if self.year:
            container.append(f"({self.year})")
        if self.pages:
            container.append(f"pp. {self.pages}.")
            
        if container:
            parts.append(" " + ", ".join(container))
        
        # Clean up and join
        citation = ' '.join(parts).replace(' .', '.').replace(' ,', ',').strip()
        return citation
    
    def _format_chicago(self) -> str:
        """Format in Chicago style."""
        parts = []
        
        # Authors
        if self.authors:
            if len(self.authors) == 1:
                parts.append(f"{self.authors[0]}.")
            elif len(self.authors) == 2:
                parts.append(f"{self.authors[0]} and {self.authors[1]}.")
            else:
                parts.append(", ".join(str(a) for a in self.authors[:-1]) + f", and {self.authors[-1]}.")
        
        # Title
        if self.title:
            parts.append(f' "{self.title}."')
        
        # Publication info
        pub_info = []
        if self.journal:
            pub_info.append(self.journal)
        if self.volume:
            pub_info.append(f"{self.volume}")
        if self.issue:
            pub_info.append(f"no. {self.issue}")
        if self.year:
            pub_info.append(f"({self.year})")
        if self.pages:
            pub_info.append(f"{self.pages}.")
        
        if pub_info:
            parts.append(" " + ", ".join(pub_info))
        
        # Clean up and join
        citation = ' '.join(parts).replace(' .', '.').replace(' ,', ',').strip()
        return citation
    
    def to_bibtex(self) -> str:
        """Convert to BibTeX format."""
        # Generate a citation key
        if self.authors and self.year and self.title:
            first_author = str(self.authors[0]).split(',')[0].lower()
            first_word = self.title.split()[0].lower()
            key = f"{first_author}{self.year}{first_word}"
        else:
            key = f"ref{hash(self) & 0xFFFFFFFF}"
        
        # Map reference type to BibTeX type
        type_map = {
            'article': 'article',
            'book': 'book',
            'chapter': 'inbook',
            'thesis': 'phdthesis',
            'report': 'techreport',
            'conference': 'inproceedings'
        }
        entry_type = type_map.get(self.pub_type, 'misc')
        
        # Build fields
        fields = []
        if self.title:
            fields.append(f"    title = {{{self.title}}}")
        if self.authors:
            authors = ' and '.join(str(a) for a in self.authors)
            fields.append(f"    author = {{{authors}}}")
        if self.year:
            fields.append(f"    year = {{{self.year}}}")
        if self.journal:
            fields.append(f"    journal = {{{self.journal}}}")
        if self.volume:
            fields.append(f"    volume = {{{self.volume}}}")
        if self.issue:
            fields.append(f"    number = {{{self.issue}}}")
        if self.pages:
            fields.append(f"    pages = {{{self.pages}}}")
        if self.publisher:
            fields.append(f"    publisher = {{{self.publisher}}}")
        if self.doi:
            fields.append(f"    doi = {{{self.doi}}}")
        if self.url:
            fields.append(f"    url = {{{self.url}}}")
        
        # Combine into BibTeX entry
        bibtex = [f"@{entry_type}{{{key},"]
        bibtex.append(",\n".join(fields))
        bibtex.append("}")
        
        return "\n".join(bibtex)
    
    def to_ris(self) -> str:
        """Convert to RIS format."""
        ris = []
        
        # Map reference type to RIS type
        type_map = {
            'article': 'JOUR',
            'book': 'BOOK',
            'chapter': 'CHAP',
            'thesis': 'THES',
            'report': 'RPRT',
            'conference': 'CPAPER'
        }
        entry_type = type_map.get(self.pub_type, 'GEN')
        
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
        if self.url:
            ris.append(f"UR  - {self.url}")
        if self.abstract:
            ris.append(f"AB  - {self.abstract}")
        if self.keywords:
            for kw in self.keywords:
                ris.append(f"KW  - {kw}")
        
        ris.append("ER  - ")
        ris.append("")
        
        return "\n".join(ris)
    
    def to_csv_row(self) -> Dict[str, str]:
        """Convert to a CSV row (dictionary of fields)."""
        return {
            'title': self.title or '',
            'authors': '; '.join(str(a) for a in self.authors) if self.authors else '',
            'year': str(self.year) if self.year else '',
            'journal': self.journal or '',
            'volume': self.volume or '',
            'issue': self.issue or '',
            'pages': self.pages or '',
            'doi': self.doi or '',
            'url': self.url or '',
            'type': self.pub_type or '',
            'publisher': self.publisher or '',
            'abstract': self.abstract or ''
        }
