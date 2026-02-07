import re
import json

def extract_book_fields(raw_reference: str) -> dict:
    # 1. Initialize Envelope
    envelope = {
        "raw_reference": raw_reference,
        "reference_type": "book",
        "type_confidence": 0.75,
        "extraction_status": "failed",
        "fields": {
            "authors":   { "value": [], "confidence": 0.0, "source": "missing" },
            "editors":   { "value": [], "confidence": 0.0, "source": "missing" },
            "year":      { "value": None, "confidence": 0.0, "source": "missing" },
            "title":     { "value": None, "confidence": 0.0, "source": "missing" },
            "publisher": { "value": None, "confidence": 0.0, "source": "missing" },
            "place":     { "value": None, "confidence": 0.0, "source": "missing" },
            "edition":   { "value": None, "confidence": 0.0, "source": "missing" },
            "isbn":      { "value": None, "confidence": 0.0, "source": "missing" }
        },
        "metadata": {
            "extractor_version": "stage2_v1",
            "notes": []
        }
    }
    
    fields = envelope["fields"]
    
    # 2. Year Extraction (Priority 1)
    # Regex: (19|20)\d{2}
    year_match = re.search(r"\(?((?:19|20)\d{2})\)?", raw_reference)
    year_end_index = 0
    year_start_index = 0
    
    if year_match:
        fields["year"] = {
            "value": int(year_match.group(1)),
            "confidence": 0.95,
            "source": "regex"
        }
        year_start_index = year_match.start()
        year_end_index = year_match.end()

    # 3. ISBN Extraction (Priority 6)
    # Regex: ISBN(?:-13)?:?\s?[0-9\-X]{10,17}
    isbn_match = re.search(r"ISBN(?:-13)?:?\s?([0-9\-X]{10,17})", raw_reference, re.IGNORECASE)
    isbn_start = len(raw_reference)
    
    if isbn_match:
        fields["isbn"] = {
            "value": isbn_match.group(1),
            "confidence": 0.95,
            "source": "regex"
        }
        isbn_start = isbn_match.start()

    # 4. Edition Extraction (Priority 5)
    # Regex: \d+(st|nd|rd|th)\s+ed(ition)?
    edition_match = re.search(r"(\d+(?:st|nd|rd|th)\s+ed(?:ition)?\.?)", raw_reference, re.IGNORECASE)
    edition_start = isbn_start
    
    if edition_match:
        fields["edition"] = {
            "value": edition_match.group(1),
            "confidence": 0.90,
            "source": "regex"
        }
        # Edition usually comes before ISBN
        edition_start = edition_match.start()
        # Update upper bound for previous fields
        if edition_start < isbn_start:
            isbn_start = edition_start # logic anchor

    # 5. Authors / Editors Extraction (Priority 3)
    # Text before year
    if year_start_index > 0:
        author_text = raw_reference[:year_start_index].strip()
        # Check for editor indicators: (ed.), (eds.), edited by
        is_editor = False
        editor_match = re.search(r"(\(eds?\.?\)|\bedited by\b)", author_text, re.IGNORECASE)
        
        if editor_match:
            is_editor = True
            # Remove the indicator for splitting
            author_text = re.sub(r"(\(eds?\.?\)|\bedited by\b)", "", author_text, flags=re.IGNORECASE)
        
        # Clean trailing parens or whitespace
        author_text = re.sub(r"[\s()]+$", "", author_text)
        
        if author_text:
            # Use robust author splitting
            try:
                from .author_splitter import split_authors
            except ImportError:
                 from author_splitter import split_authors

            people = split_authors(author_text)
            
            if people:
                target_field = "editors" if is_editor else "authors"
                fields[target_field] = {
                    "value": people,
                    "confidence": 0.85,
                    "source": "heuristic"
                }

    # 6. Title, Publisher, Place Strategy (Priority 2 & 4)
    # Search space: Text AFTER year, BEFORE edition/ISBN
    if year_end_index > 0:
        search_start = year_end_index
        search_end = edition_start
        relevant_text = raw_reference[search_start:search_end].strip().strip(".,")
        
        # Title Detection
        # 1. Quoted/Italic
        title_val = None
        title_conf = 0.0
        title_source = "missing"
        remaining_after_title = relevant_text
        
        # Check quotes
        quote_match = re.search(r"['\"](.*?)['\"]", relevant_text)
        # Check italics (markdown style * or _) - though raw string likely plain text, 
        # sometimes encoded. Assuming plain text for now, prioritising heuristic.
        
        if quote_match:
            title_val = quote_match.group(1)
            title_conf = 0.90
            title_source = "regex"
            remaining_after_title = relevant_text[quote_match.end():].strip()
        else:
            # Heuristic: Title is text up to the first dot?
            # Or Title is text before "Place: Publisher"
            # Look for Place: Publisher pattern (City: Publisher)
            # Pattern: (Word <maybe spaces> Word): (Capitalized String)
            place_pub_match = re.search(r"([A-Za-z\s\.]+):\s*([A-Za-z0-9\s,&]+)$", relevant_text)
            
            if place_pub_match:
                # Everything before this match is likely the title
                possible_title = relevant_text[:place_pub_match.start()].strip().strip(".")
                if possible_title:
                    title_val = possible_title
                    title_conf = 0.80 # High confidence if structure fits
                    title_source = "heuristic"
                    remaining_after_title = relevant_text[place_pub_match.start():]
            else:
                # Fallback: Split by first full stop if no colon pattern found
                parts = relevant_text.split('.', 1)
                if len(parts) > 0:
                    title_val = parts[0].strip()
                    title_conf = 0.70
                    title_source = "heuristic"
                    if len(parts) > 1:
                        remaining_after_title = parts[1].strip()
                    else:
                        remaining_after_title = ""

        if title_val:
            fields["title"] = {
                "value": title_val,
                "confidence": title_conf,
                "source": title_source
            }

        # Publisher & Place
        # Analyze remaining_after_title
        # Expect "Place: Publisher" or "Publisher"
        
        pub_val = None
        place_val = None
        
        if remaining_after_title:
            # Clean leading punctuation
            cleaned_rem = remaining_after_title.strip(":., ")
            
            # Check for Place: Publisher
            pp_match = re.search(r"^([A-Za-z\s\.]+):\s*([A-Za-z0-9\s,&]+)$", cleaned_rem)
            
            if pp_match:
                place_val = pp_match.group(1).strip()
                pub_val = pp_match.group(2).strip()
                fields["place"] = { "value": place_val, "confidence": 0.70, "source": "heuristic" }
                fields["publisher"] = { "value": pub_val, "confidence": 0.85, "source": "heuristic" }
            else:
                # Assume just Publisher if no colon
                # Or try to detect known headers? No, assume remaining is Publisher
                # Only if capitalized
                if cleaned_rem[0].isupper():
                    fields["publisher"] = { "value": cleaned_rem, "confidence": 0.75, "source": "heuristic" }

    # 7. Status Logic
    # IF (authors OR editors) AND year AND title AND publisher >= 0.8
    has_people = (fields["authors"]["confidence"] >= 0.8 or fields["editors"]["confidence"] >= 0.8)
    has_year = fields["year"]["confidence"] >= 0.8
    has_title = fields["title"]["confidence"] >= 0.8
    has_pub = fields["publisher"]["confidence"] >= 0.8
    
    complete = has_people and has_year and has_title and has_pub
    
    # Partial: at least one of THOSE fields extracted (confidence > 0)
    # The requirement says "at least one of those fields extracted", assuming > 0
    any_people = (fields["authors"]["confidence"] > 0 or fields["editors"]["confidence"] > 0)
    any_year = fields["year"]["confidence"] > 0
    any_title = fields["title"]["confidence"] > 0
    any_pub = fields["publisher"]["confidence"] > 0
    
    partial = any_people or any_year or any_title or any_pub
    
    if complete:
        envelope["extraction_status"] = "complete"
    elif partial:
        envelope["extraction_status"] = "partial"
    else:
        envelope["extraction_status"] = "failed"
        
    return envelope

# TEST CASES
if __name__ == "__main__":
    t1 = "Goodfellow, I., Bengio, Y. and Courville, A. (2016) Deep Learning. Cambridge, MA: MIT Press."
    t2 = "Smith, J. (2020) \"Messy Book Reference\" 2nd Edition."

    print("--- Test Case 1 ---")
    print(json.dumps(extract_book_fields(t1), indent=2, default=str))
    
    print("\n--- Test Case 2 ---")
    print(json.dumps(extract_book_fields(t2), indent=2, default=str))
