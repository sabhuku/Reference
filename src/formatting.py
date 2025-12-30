"""Citation and reference formatting utilities."""
from typing import List, Optional
from .models import Publication

def format_harvard_authors(authors: List[str]) -> str:
    """Format author list in Harvard style."""
    if not authors:
        return "UNKNOWN"
    if len(authors) == 1:
        return authors[0]
    if len(authors) == 2:
        return " and ".join(authors)
    return ", ".join(authors[:-1]) + " and " + authors[-1]

def format_apa_authors(authors: List[str]) -> str:
    """Format author list in APA style."""
    if not authors:
        return "UNKNOWN"
    if len(authors) == 1:
        return authors[0]
    if len(authors) == 2:
        return authors[0] + ", & " + authors[1]
    return ", ".join(authors[:-1]) + ", & " + authors[-1]

def format_ieee_authors(authors: List[str]) -> str:
    """Format author list in IEEE style."""
    if not authors:
        return "UNKNOWN"
    
    def flip_name(author: str) -> str:
        """Convert 'Surname, Given' to 'G. Surname'."""
        if "," in author:
            family, given = [x.strip() for x in author.split(",", 1)]
        else:
            parts = author.split()
            if len(parts) == 1:
                return parts[0]
            family = parts[-1]
            given = " ".join(parts[:-1])
        initials = " ".join([p[0] + "." for p in given.split() if p])
        return f"{initials} {family}".strip()
    
    flipped = [flip_name(x) for x in authors]
    
    if len(flipped) == 1:
        return flipped[0]
    if len(flipped) == 2:
        return flipped[0] + " and " + flipped[1]
    return ", ".join(flipped[:-1]) + ", and " + flipped[-1]

class CitationFormatter:
    """Format citations and references in different styles."""
    
    @staticmethod
    def in_text_citation(pub: Publication, style: str, index: Optional[int] = None) -> str:
        """Generate in-text citation."""
        if style == "ieee":
            return f"[{index if index is not None else '?'}]"
            
        if not pub.authors:
            return "(UNKNOWN)"
            
        first_author = pub.authors[0].split(",")[0].strip()
        
        if len(pub.authors) > 2:
            return f"({first_author} et al., {pub.year})"
            
        if len(pub.authors) == 2:
            second_author = pub.authors[1].split(",")[0].strip()
            if style == "apa":
                return f"({first_author} & {second_author}, {pub.year})"
            return f"({first_author} and {second_author}, {pub.year})"
            
        return f"({first_author}, {pub.year})"
    
    @staticmethod
    def reference_entry(pub: Publication, style: str, index: Optional[int] = None) -> str:
        """Generate full reference entry."""
        is_article = (
            pub.pub_type in ["journal-article", "article-journal", "proceedings-article"]
            or bool(pub.journal)
        )
        
        if style == "harvard":
            return CitationFormatter._harvard_reference(pub, is_article)
        if style == "apa":
            return CitationFormatter._apa_reference(pub, is_article)
        if style == "ieee":
            return CitationFormatter._ieee_reference(pub, is_article, index)
        
        return "UNKNOWN STYLE"
    
    @staticmethod
    def _harvard_reference(pub: Publication, is_article: bool) -> str:
        """Format reference in Harvard style."""
        if is_article:
            author_str = format_harvard_authors(pub.authors)
            vol_issue = ""
            if pub.volume and pub.issue:
                vol_issue = f"{pub.volume}({pub.issue})"
            elif pub.volume:
                vol_issue = pub.volume
            elif pub.issue:
                vol_issue = f"({pub.issue})"
            
            pages = f"pp. {pub.pages}" if pub.pages else ""
            result = f"{author_str} ({pub.year}) '{pub.title}', {pub.journal}"
            
            if vol_issue:
                result += f", {vol_issue}"
            if pages:
                result += f", {pages}"
            if pub.doi:
                result += f". doi:{pub.doi}"
            else:
                result += "."
                
            return result
        else:
            author_str = format_harvard_authors(pub.authors)
            result = f"{author_str} ({pub.year}) {pub.title}."
            if pub.publisher:
                result += f" {pub.publisher}."
            return result
    
    @staticmethod
    def _apa_reference(pub: Publication, is_article: bool) -> str:
        """Format reference in APA style."""
        if is_article:
            author_str = format_apa_authors(pub.authors)
            vol_issue = ""
            if pub.volume and pub.issue:
                vol_issue = f"{pub.volume}({pub.issue})"
            elif pub.volume:
                vol_issue = pub.volume
            elif pub.issue:
                vol_issue = f"({pub.issue})"
            
            result = f"{author_str} ({pub.year}). {pub.title}. {pub.journal}"
            
            if vol_issue:
                result += f", {vol_issue}"
            if pub.pages:
                result += f", {pub.pages}"
            if pub.doi:
                result += f". https://doi.org/{pub.doi}"
            else:
                result += "."
                
            return result
        else:
            author_str = format_apa_authors(pub.authors)
            result = f"{author_str} ({pub.year}). {pub.title}."
            if pub.publisher:
                result += f" {pub.publisher}."
            return result
    
    @staticmethod
    def _ieee_reference(pub: Publication, is_article: bool, index: Optional[int]) -> str:
        """Format reference in IEEE style."""
        num_label = f"[{index if index is not None else '?'}]"
        author_str = format_ieee_authors(pub.authors)
        
        if is_article:
            parts = [f"{num_label} {author_str}, \"{pub.title}\","]
            
            if pub.journal:
                parts.append(f"{pub.journal},")
            if pub.volume:
                parts.append(f"vol. {pub.volume},")
            if pub.issue:
                parts.append(f"no. {pub.issue},")
            if pub.pages:
                parts.append(f"pp. {pub.pages},")
                
            parts.append(f"{pub.year}.")
            return " ".join(parts)
        else:
            return f"{num_label} {author_str}, {pub.title}, {pub.publisher}, {pub.year}."