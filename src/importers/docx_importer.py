"""DOCX Importer for extracting references from Word documents."""
import re
from io import BytesIO
from typing import List, Union
from docx import Document

from .base import ReferenceImporter
from ..models import Publication

class DocxImporter(ReferenceImporter):
    """Importer for Microsoft Word .docx files."""
    
    def parse(self, content: Union[str, bytes, BytesIO]) -> List[Publication]:
        """
        Parse DOCX content into references.
        
        Args:
            content: Can be file path (str), bytes, or BytesIO.
                     If str, assumes path. If bytes, wraps in BytesIO.
        """
        pubs = []
        
        # Handle input types
        if isinstance(content, str):
            # If it's a path, open it? 
            # Or if it's "content string" (which app.py passes for others), DOCX can't handle string content.
            # We assume app.py modification will pass bytes or stream.
            # But just in case it passes a path:
            if content.endswith('.docx'):
                stream = content
            else:
                # If 'str' is passed but it's not a path (e.g. garbage text), we can't process it as DOCX
                return [] 
        elif isinstance(content, bytes):
            stream = BytesIO(content)
        else:
            # Assume file-like
            stream = content
            
        try:
            doc = Document(stream)
        except Exception as e:
            # Not a valid docx
            return []

        # Helper regex
        auth_year_pattern = re.compile(r"^(.+?)\s+\((.+?)\)\s+(.+)$")
        url_pattern = re.compile(r"Available at\s*:?\s*(https?://[^\s\)]+)", re.IGNORECASE)
        access_date_pattern = re.compile(r"\(Accessed\s*:?\s*(.+?)\)", re.IGNORECASE)
        editor_pattern = re.compile(r"in\s+(.+?)\s+\(eds?\.?\)", re.IGNORECASE)
        type_tag_pattern = re.compile(r"\[(Photograph|Instagram|Online image|Video|Audio)\]", re.IGNORECASE)
        pages_pattern = re.compile(r"pp\.\s*(\d+[-–]\d+)")

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            
            # Extract Authors and Year
            match = auth_year_pattern.match(text)
            if not match:
                continue
                
            raw_auth, raw_year, remainder = match.groups()
            
            # Validation: strict year
            if not re.search(r'\d{4}', raw_year):
                continue
            
            # Determine Title and Source Boundary
            # Logic: If it starts with a quote, find the closing quote.
            # Otherwise find the first period followed by a space.
            title = ""
            raw_source = ""
            
            remainder = remainder.strip()
            if remainder.startswith(("'","‘","\"","“")):
                quote_char = remainder[0]
                # Map to closing quote
                closing_map = {"'":"'", "‘":"’", "\"":"\"", "“":"”"}
                closing_char = closing_map.get(quote_char, quote_char)
                
                # Find closing quote that is NOT immediately followed by a letter (to avoid contractions like 'Don't')
                # Actually, in Harvard, the title usually ends with quote then comma or period.
                end_idx = -1
                for i in range(1, len(remainder)):
                    if remainder[i] == closing_char:
                        # Check if it looks like the end of title (quote followed by comma, period, or space)
                        if i + 1 >= len(remainder) or remainder[i+1] in [",", ".", " "]:
                            end_idx = i
                            break
                
                if end_idx != -1:
                    title = remainder[1:end_idx].strip()
                    raw_source = remainder[end_idx+1:].strip().lstrip(",").lstrip(".").strip()
                else:
                    # Fallback to period split
                    parts = remainder.split('. ', 1)
                    title = parts[0]
                    raw_source = parts[1] if len(parts) > 1 else ""
            else:
                # No leading quote
                parts = remainder.split('. ', 1)
                if len(parts) > 1:
                    title = parts[0]
                    raw_source = parts[1]
                elif ':' in remainder:
                    # Case: Effective Communication Dublin: Gill and Macmillan
                    # We look for the colon. The word before it is likely the location.
                    # We'll split the title and source at the "Location:" boundary.
                    colon_idx = remainder.find(':')
                    # Look for the space before the location
                    space_idx = remainder.rfind(' ', 0, colon_idx)
                    if space_idx != -1:
                        title = remainder[:space_idx].strip()
                        raw_source = remainder[space_idx:].strip()
                    else:
                        title = remainder[:colon_idx].strip()
                        raw_source = remainder[colon_idx:].strip()
                else:
                    title = remainder
                    raw_source = ""

            # Extraction
            authors = [raw_auth.strip()]
            
            # URL and Access Date
            url_match = url_pattern.search(text)
            url = url_match.group(1).rstrip('.') if url_match else ""
            
            access_match = access_date_pattern.search(text)
            access_date = access_match.group(1).rstrip('.') if access_match else ""
            
            # Editor
            # Extract accurately: ' in [Editor] (ed.)
            editor = ""
            editor_match = editor_pattern.search(text)
            if editor_match:
                editor = editor_match.group(1).strip()
                # If there's a leading quote/title fragment, clean it
                if "in " in editor.lower():
                    editor = re.split(r"in\s+", editor, flags=re.IGNORECASE)[-1]
            
            # Pages
            pages_match = pages_pattern.search(text)
            pages = pages_match.group(1) if pages_match else ""
            
            # Edition (e.g., "4th edn.", "2nd edition")
            edition_pattern = re.compile(r'(\d+(?:st|nd|rd|th)\s+edn?\.?)', re.IGNORECASE)
            edition_match = edition_pattern.search(text)
            edition = edition_match.group(1) if edition_match else ""
            
            # Collection (e.g., "Safari Books Online [Online]", "ACM Digital Library [Online]")
            collection_pattern = re.compile(r'([A-Z][A-Za-z\s]+(?:Online|Library|Collection))\s*\[Online\]', re.IGNORECASE)
            collection_match = collection_pattern.search(text)
            collection = collection_match.group(1).strip() if collection_match else ""

            # Type Heuristics
            type_tag_match = type_tag_pattern.search(text)
            if type_tag_match:
                pub_type = type_tag_match.group(1).lower()
            elif editor:
                pub_type = "chapter"
            elif "forum" in raw_source.lower() or "forum" in title.lower():
                pub_type = "forum-post"
            elif re.search(r'[A-Z]\d{3}:', text): 
                pub_type = "module-material"
            elif url:
                pub_type = "webpage"
            else:
                # Conference detection
                conference_keywords = ['conference', 'proceedings', 'symposium', 'workshop', 'congress']
                has_conference = any(kw in raw_source.lower() for kw in conference_keywords)
                
                if has_conference:
                    pub_type = "conference"
                else:
                    # Original logic fallback
                    # Refined: ignore colons if they look like they are part of a URL/URI
                    remainder_no_url = re.sub(r'https?://[^\s]+', '', raw_source)
                    is_book_structure = ':' in remainder_no_url and not any(x in raw_source.lower() for x in ['vol', 'no.', 'pp.', 'page'])
                    has_publisher_keyword = any(kw in raw_source.lower() for kw in ["press", "publisher", "university"])
                    has_journal_indicators = any(kw in raw_source.lower() for kw in ["journal", "vol", "no.", "pp.", "review"])
                    
                    if has_publisher_keyword or is_book_structure:
                        pub_type = "book"
                    elif has_journal_indicators or re.search(r'\d+\(\d+\)', raw_source):
                        pub_type = "article"
                    else:
                        pub_type = "book" if not re.search(r'\d', raw_source) else "article"

            # Clean Source info
            cleaned_source = re.sub(r"(Available at:?|Available from:?).*$", "", raw_source, flags=re.IGNORECASE).strip().rstrip('.')
            # Also clean pages from cleaned_source if they were extracted
            if pages:
                 cleaned_source = re.sub(r"pp\.\s*\d+[-–]\d+", "", cleaned_source).strip().rstrip(',').strip()
            
            journal = ""
            publisher = ""
            location = ""
            conference_name = ""
            conference_location = ""
            conference_date = ""
            
            if pub_type == "article":
                journal = cleaned_source.split(',')[0].strip()
            elif pub_type == "chapter" and editor:
                source_parts = re.split(fr"\(eds?\.?\)", cleaned_source, flags=re.IGNORECASE)
                if len(source_parts) > 1:
                    remaining = source_parts[1].strip().lstrip('.').strip().lstrip(',').strip()
                    publisher_match = re.search(r'^([^,.]+)', remaining)
                    publisher = publisher_match.group(1).strip() if publisher_match else remaining
                    journal = remaining.split('.')[0]
            elif pub_type == "conference":
                # Extract conference details: Conference Name, Location, Date, pp. X-Y
                # Pattern: "International Conference on AI, London, UK, 15-17 June"
                parts = cleaned_source.split(',')
                if len(parts) >= 1:
                    conference_name = parts[0].strip()
                if len(parts) >= 2:
                    # Try to detect location (usually has country or city)
                    potential_location = []
                    for i in range(1, len(parts)):
                        part = parts[i].strip()
                        # Stop if we hit a date pattern
                        if re.search(r'\d+[-–]\d+\s+\w+|\w+\s+\d{4}', part):
                            conference_date = part
                            break
                        potential_location.append(part)
                    conference_location = ', '.join(potential_location) if potential_location else ""
                journal = conference_name  # Use conference name as journal for compatibility
            elif pub_type == "book":
                if ':' in cleaned_source:
                    parts = cleaned_source.split(':', 1)
                    location = parts[0].strip()
                    publisher = parts[1].strip()
                else:
                    publisher = cleaned_source
            else:
                journal = cleaned_source
            
            p = Publication(
                source="docx_import",
                pub_type=pub_type,
                authors=authors,
                year=raw_year,
                title=title.strip("'\"‘“\"'").strip(),
                journal=journal or cleaned_source,
                publisher=publisher,
                location=location,
                volume="",
                issue="",
                pages=pages,
                doi="",
                url=url,
                access_date=access_date,
                editor=editor,
                edition=edition,
                collection=collection,
                conference_name=conference_name,
                conference_location=conference_location,
                conference_date=conference_date
            )
            pubs.append(p)
                
        return pubs
