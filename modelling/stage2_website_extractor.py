import re
import json
from datetime import datetime

def extract_website_fields(raw_reference: str) -> dict:
    # 1. Initialize Envelope
    envelope = {
        "raw_reference": raw_reference,
        "reference_type": "website",
        "type_confidence": 0.75,
        "extraction_status": "failed",
        "fields": {
            "author":        { "value": None, "confidence": 0.0, "source": "missing" },
            "organisation": { "value": None, "confidence": 0.0, "source": "missing" },
            "year":          { "value": None, "confidence": 0.0, "source": "missing" },
            "title":         { "value": None, "confidence": 0.0, "source": "missing" },
            "url":           { "value": None, "confidence": 0.0, "source": "missing" },
            "access_date":   { "value": None, "confidence": 0.0, "source": "missing" }
        },
        "metadata": {
            "extractor_version": "stage2_v1",
            "notes": []
        }
    }
    
    fields = envelope["fields"]
    
    # 2. URL Extraction (Priority 1)
    # Regex: https?://[^\s]+
    # Note: URL often ends with ) or . if at end of string, need to handle that.
    # But strict regex was requested: https?://[^\s]+
    # I'll modify slightly to trim trailing punctuation often found in refs like ). or .
    url_match = re.search(r"(https?://[^\s]+)", raw_reference)
    url_start = len(raw_reference)
    
    if url_match:
        url_val = url_match.group(1).rstrip(").,")
        fields["url"] = {
            "value": url_val,
            "confidence": 0.95,
            "source": "regex"
        }
        url_start = url_match.start()

    # 3. Access Date Extraction (Priority 2)
    # Patterns like (Accessed: 1 August 2024)
    # Convert to ISO format YYYY-MM-DD
    access_match = re.search(r"\(Accessed:?\s*(.*?)\)", raw_reference, re.IGNORECASE)
    
    if access_match:
        date_str = access_match.group(1).strip()
        # Try parse
        try:
            # Try formats like "1 August 2024", "August 1, 2024" etc.
            # Simple heuristic parser for explicit example: "1 August 2024" -> "%d %B %Y"
            dt = datetime.strptime(date_str, "%d %B %Y")
            iso_date = dt.strftime("%Y-%m-%d")
            
            fields["access_date"] = {
                "value": iso_date,
                "confidence": 0.90,
                "source": "regex"
            }
        except ValueError:
            # Fallback or keep raw if strict ISO required? 
            # Request says "Convert to ISO format", implies if fail, maybe don't set or set raw?
            # "Each successful extraction sets value". I'll assume only set if successful conversion.
            pass

    # 4. Year Extraction (Priority 3)
    # Regex: (19|20)\d{2}
    # Note: If found in access date, we shouldn't use it as publication year unless explicitly separated.
    # Search for year outside of access date pattern?
    # Simple strategy: Find all years, pick one that is NOT the access year if possible, or position based.
    # Traditionally, year comes after author/title in Harvard style.
    
    # Find all years
    year_iter = re.finditer(r"\(?((?:19|20)\d{2})\)?", raw_reference)
    found_years = []
    for m in year_iter:
        # Check if this year is part of the access date match
        if access_match and m.start() >= access_match.start() and m.end() <= access_match.end():
            continue
        found_years.append(m)
        
    year_end_index = 0
    year_start_index = 0
    
    if found_years:
        # Take the first candidate year
        y_match = found_years[0]
        fields["year"] = {
            "value": int(y_match.group(1)),
            "confidence": 0.95,
            "source": "regex"
        }
        year_start_index = y_match.start()
        year_end_index = y_match.end()
    else:
        # If inferred from access date -> confidence <= 0.60
        if fields["access_date"]["value"]:
            # Extract year from ISO date
            inferred_year = int(fields["access_date"]["value"][:4])
            fields["year"] = {
                "value": inferred_year,
                "confidence": 0.60,
                "source": "inferred"
            }

    # 5. Title Extraction (Priority 4)
    # Text before "Available at:" or before "URL"
    # Search space: Text AFTER year (if exists) UP TO URL or "Available at"
    
    search_start = year_end_index
    # Find "Available at" or URL start
    limit_index = url_start
    avail_match = re.search(r"Available at:", raw_reference, re.IGNORECASE)
    if avail_match and avail_match.start() < limit_index:
        limit_index = avail_match.start()
        
    relevant_text = raw_reference[search_start:limit_index].strip(" .,")
    
    # Strategy: Quoted text preferred
    title_val = None
    title_conf = 0.0
    title_source = "missing"
    
    quote_match = re.search(r"['\"](.*?)['\"]", relevant_text)
    if quote_match:
        title_val = quote_match.group(1)
        title_conf = 0.90
        title_source = "regex"
    elif relevant_text:
        # Fallback: take the whole chunk
        title_val = relevant_text
        title_conf = 0.70 # Heuristic
        title_source = "heuristic"
        
    if title_val:
        fields["title"] = {
            "value": title_val,
            "confidence": title_conf,
            "source": title_source
        }

    # 6. Author / Organisation Extraction (Priority 5 & 6)
    # Text before year
    if year_start_index > 0:
        author_text = raw_reference[:year_start_index].strip()
        # Clean trailing parens or whitespace
        author_text = re.sub(r"[\s()]+$", "", author_text)
        
        if author_text:
            # Heuristic: If it looks like a person name (comma format) -> Author
            # If capitalized entity -> Organisation
            # Or just set Author and fallback Org? "Organisation may substitute for author"
            # Schema has both. 
            # Priority: Author named individual... Organisation capitalised entity... Use Org only if Author not found.
            
            # Simple heuristic: If contains " ", and maybe punctuation?
            # "Smith, J." vs "RSPCA"
            
            # Check for comma (Name, Initials)
            if "," in author_text:
                 # Check if it looks like author list
                 fields["author"] = {
                     "value": [a.strip() for a in re.split(r",\s*|\s+and\s+|&", author_text) if a.strip()],
                     "confidence": 0.70,
                     "source": "heuristic"
                 }
            else:
                # Assume Organisation if no comma structure typical of authors
                # Or assume Author if it's one word? "RSPCA".
                # "Organisation may substitute for author" -> field "organisation"
                
                # Let's set Organisation if it looks like a Org name (no commas)
                fields["organisation"] = {
                    "value": author_text,
                    "confidence": 0.70,
                    "source": "heuristic"
                }

    # 7. Status Logic
    # IF title AND url have confidence >= 0.8
    complete = (fields["title"]["confidence"] >= 0.8 and fields["url"]["confidence"] >= 0.8)
    
    # Partial: at least one field extracted
    partial = any(fields[k]["confidence"] > 0 for k in fields)
    
    if complete:
        envelope["extraction_status"] = "complete"
    elif partial:
        envelope["extraction_status"] = "partial"
    else:
        envelope["extraction_status"] = "failed"
        
    return envelope

# TEST CASES
if __name__ == "__main__":
    t1 = "RSPCA (2024) Caring for cats and kittens. Available at: https://www.rspca.org.uk (Accessed: 1 August 2024)."
    t2 = "OpenAI. \"ChatGPT\". https://chat.openai.com (Accessed: 5 February 2024)."

    print("--- Test Case 1 ---")
    print(json.dumps(extract_website_fields(t1), indent=2, default=str))
    
    print("\n--- Test Case 2 ---")
    print(json.dumps(extract_website_fields(t2), indent=2, default=str))
