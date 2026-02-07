import re
import json

def extract_journal_fields(raw_reference: str) -> dict:
    # 1. Initialize Envelope
    envelope = {
        "raw_reference": raw_reference,
        "reference_type": "journal",
        "type_confidence": 0.75,
        "extraction_status": "failed",
        "fields": {
            "authors": { "value": [], "confidence": 0.0, "source": "missing" },
            "year": { "value": None, "confidence": 0.0, "source": "missing" },
            "title": { "value": None, "confidence": 0.0, "source": "missing" },
            "journal": { "value": None, "confidence": 0.0, "source": "missing" },
            "volume": { "value": None, "confidence": 0.0, "source": "missing" },
            "issue": { "value": None, "confidence": 0.0, "source": "missing" },
            "pages": { "value": None, "confidence": 0.0, "source": "missing" },
            "doi": { "value": None, "confidence": 0.0, "source": "missing" }
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

    # 3. Title Extraction (Priority 2)
    # Quoted text '...' or "..."
    title_match = re.search(r"['\"](.*?)['\"]", raw_reference)
    title_end_index = 0
    
    if title_match:
        fields["title"] = {
            "value": title_match.group(1),
            "confidence": 0.90,
            "source": "regex"
        }
        title_end_index = title_match.end()

    # 4. Authors Extraction (Priority 3)
    # Text before year
    if year_start_index > 0:
        author_text = raw_reference[:year_start_index].strip()
        # Clean trailing parens or whitespace
        author_text = re.sub(r"[\s()]+$", "", author_text)
        
        if author_text:
            # Use robust author splitting
            try:
                from .author_splitter import split_authors
            except ImportError:
                 from author_splitter import split_authors

            authors = split_authors(author_text)
            
            if authors:
                fields["authors"] = {
                    "value": authors,
                    "confidence": 0.85, # Corroborated by position before year
                    "source": "heuristic"
                }

    # 5. DOI Extraction (Priority 6 - moved up for bounds check)
    # Regex: 10.\d{4,9}/[-._;()/:A-Z0-9]+
    doi_match = re.search(r"(10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+)", raw_reference)
    if doi_match:
        fields["doi"] = {
            "value": doi_match.group(1),
            "confidence": 0.95,
            "source": "regex"
        }

    # 6. Journal, Volume, Issue, Pages
    # Search space: Text AFTER title
    if title_end_index > 0:
        search_start = title_end_index
        search_end = doi_match.start() if doi_match else len(raw_reference)
        relevant_text = raw_reference[search_start:search_end].strip()
        
        # Volume / Issue Pattern
        # 9(8) or Vol. 9
        vi_match = re.search(r"(?:Vol\.?\s*(\d+))|(\b\d+)\s*\(\s*(\d+)\s*\)", relevant_text)
        
        if vi_match:
            vol = vi_match.group(1) or vi_match.group(2)
            issue = vi_match.group(3)
            
            if vol:
                fields["volume"] = { "value": vol, "confidence": 0.85, "source": "regex" }
            if issue:
                fields["issue"] = { "value": issue, "confidence": 0.85, "source": "regex" }
        
        # Pages Pattern
        # pp. 123-145 or : 123-145
        p_match = re.search(r"(?:pp\.?|:)\s*(\d+(?:-\d+)?)|(\d+-\d+)", relevant_text)
        if p_match:
            pages = p_match.group(1) or p_match.group(2)
            fields["pages"] = { "value": pages, "confidence": 0.85, "source": "regex" }

        # Journal Extraction
        # Text after title, before volume/pages
        # Determine end of journal string
        journal_end = len(relevant_text)
        if vi_match:
            journal_end = min(journal_end, vi_match.start())
        if p_match:
            journal_end = min(journal_end, p_match.start())
            
        journal_str = relevant_text[:journal_end].strip(" ,.")
        
        if journal_str:
            # If constrained by regex matches on both sides (Title AND Volume/Pages), confidence bumps to 0.8
            conf = 0.80 if (title_end_index > 0 and (vi_match or p_match)) else 0.70
            
            fields["journal"] = {
                "value": journal_str,
                "confidence": conf,
                "source": "heuristic"
            }

    # 7. Status Logic
    req_fields = ["authors", "year", "title", "journal"]
    complete = all(fields[k]["confidence"] >= 0.8 for k in req_fields)
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
    t1 = "Hochreiter, S. and Schmidhuber, J. (1997) 'Long short-term memory', Neural Computation, 9(8), pp.1735-1780."
    t2 = "Smith, J. (2020) \"Bad Reference\", Some Journal."

    print("--- Test Case 1 ---")
    print(json.dumps(extract_journal_fields(t1), indent=2, default=str))
    
    print("\n--- Test Case 2 ---")
    print(json.dumps(extract_journal_fields(t2), indent=2, default=str))
