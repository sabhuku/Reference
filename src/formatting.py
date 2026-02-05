"""Citation and reference formatting utilities."""
from typing import List, Optional
from .models import Publication

def format_harvard_authors(authors: List[str]) -> str:
    """Format author list in Harvard style."""
    if not authors:
        return "UNKNOWN"
    # Check if authors are already in "Surname, I." format (roughly)
    # If standard harvard join:
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
            pub.pub_type in ["journal-article", "article-journal", "proceedings-article", "article"]
        )
        # Exception: if it's not a book and HAS a journal, it might be an article
        if not is_article and pub.pub_type not in ["book", "chapter"]:
             if pub.journal and not pub.publisher:
                 is_article = True

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
        # Use normalized authors if available
        auths = pub.normalized_authors if getattr(pub, 'normalized_authors', None) else pub.authors
        author_str = format_harvard_authors(auths)
        
        # Determine year string
        year_str = pub.year
        if hasattr(pub, 'year_status') and pub.year_status == 'explicitly_undated':
            year_str = "n.d."
        elif not year_str:
            year_str = "no date"

        if is_article:
            vol_issue = ""
            if pub.volume and pub.issue:
                vol_issue = f"{pub.volume}({pub.issue})"
            elif pub.volume:
                vol_issue = pub.volume
            elif pub.issue:
                vol_issue = f"({pub.issue})"
            
            pages = f"pp. {pub.pages}" if pub.pages else ""
            result = f"{author_str} ({year_str}) '{pub.title}', {pub.journal}"
            
            if vol_issue:
                result += f", {vol_issue}"
            if pages:
                result += f", {pages}"
            if pub.doi:
                result += f". doi:{pub.doi}"
            elif pub.url:
                result += f". Available at: {pub.url}"
                if pub.access_date:
                    result += f" (Accessed: {pub.access_date})"
                result += "."
            else:
                result += "."
                
            return result
        else:
            # Check for Chapter
            if pub.pub_type == "chapter" and pub.editor:
                pages = f"pp. {pub.pages}" if pub.pages else ""
                # Chapter titles HAVE quotes in Harvard
                result = f"{author_str} ({year_str}) '{pub.title}', in {pub.editor} (ed.) {pub.journal}."
                if pub.publisher:
                    result += f" {pub.publisher}"
                if pages:
                    result += f", {pages}"
                result = result.rstrip('.') + "."
                return result

            # Books do NOT have quotes in Harvard, others DO
            if pub.pub_type == "book":
                result = f"{author_str} ({year_str}) {pub.title}."
                if pub.location:
                    result += f" {pub.location}:"
            elif pub.pub_type == "conference":
                # Conference papers: Author (Year) 'Title', Conference Name, Location, Date, pp. X-Y.
                result = f"{author_str} ({year_str}) '{pub.title}'"
                if pub.conference_name:
                    result += f", {pub.conference_name}"
                if pub.conference_location:
                    result += f", {pub.conference_location}"
                if pub.conference_date:
                    result += f", {pub.conference_date}"
                if pub.pages:
                    result += f", pp. {pub.pages}"
                result += "."
                return result
            else:
                result = f"{author_str} ({year_str}) '{pub.title}', {pub.journal}."
                result = result.replace(", .", ".").replace("..", ".")

            if pub.publisher:
                result += f" {pub.publisher}."
            
            if pub.url:
                result += f" Available at: {pub.url}"
                if pub.access_date:
                    result += f" (Accessed: {pub.access_date})"
                result += "."
                
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

    @staticmethod
    def format_reference(ref_data, style: str) -> str:
        """Format a reference from dict or Publication object."""
        if isinstance(ref_data, dict):
             # Robust conversion
             authors = ref_data.get('authors', [])
             if isinstance(authors, str):
                 authors = [authors]
                 
             pub = Publication(
                 source=ref_data.get('source', 'manual'),
                 pub_type=ref_data.get('pub_type', 'unknown'),
                 authors=authors,
                 year=str(ref_data.get('year', '')),
                 title=ref_data.get('title', ''),
                 journal=ref_data.get('journal', ''),
                 publisher=ref_data.get('publisher', ''),
                 location=ref_data.get('location', ''),
                 volume=str(ref_data.get('volume', '')),
                 issue=str(ref_data.get('issue', '')),
                 pages=str(ref_data.get('pages', '')),
                 doi=ref_data.get('doi', ''),
                 url=ref_data.get('url', ''),
             )
        else:
            pub = ref_data
            
        return CitationFormatter.reference_entry(pub, style)