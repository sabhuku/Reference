
import re
import json
from typing import Dict, Any, List, Optional

def remediate_reference(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stage 3: Assistive Generative Remediation.
    
    analyzes a reference that Stage 2 partially extracted or failed, 
    and generates conservative, confidence-bounded suggestions.
    
    Constraints:
    - Never overwrite Stage 2 fields.
    - Max confidence 0.7 (strong but uncertain).
    - Always requires review.
    """
    raw_ref = input_data.get("raw_reference", "")
    ref_type = input_data.get("reference_type", "unknown")
    stage2 = input_data.get("stage2_output", {})
    s2_fields = stage2.get("fields", {})
    status = stage2.get("extraction_status", "failed")

    # Fix 1: Explicit Stage 3 Gate
    if status == "complete":
        return {
            "suggested_fields": {},
            "overall_confidence": 0.0,
            "requires_review": False,
            "notes": ["Stage 3 skipped: Stage 2 extraction complete."]
        }
    
    # Initialize Output
    suggestions = {}
    notes = []
    
    # 1. Author Remediation (Heuristic/Fuzzy)
    # 1. Author Remediation (Heuristic/Fuzzy)
    # Fix 2: Explicitly check for field absence/emptiness
    if (("authors" not in s2_fields or not s2_fields["authors"].get("value")) 
        and ref_type in ["journal", "book"]):
        # Logic: Look for text before the year.
        # Stage 2 failed, so it might be messy.
        # We try a permissive split.
        year_match = re.search(r"\(?(?:19|20)\d{2}\)?", raw_ref)
        if year_match:
            pre_year = raw_ref[:year_match.start()].strip()
            # Heuristic: Clean up specific failures
            cleaned = re.sub(r"[\(\)]", "", pre_year).strip()
            if cleaned:
                # Suggest the whole block as a candidate if splitting is hard
                # Or try fuzzy split
                fuzzy_split = [p.strip() for p in re.split(r"[,&]|\sand\s", cleaned) if len(p.strip()) > 2]
                
                cands = []
                if fuzzy_split:
                    cands.append({
                        "value": fuzzy_split,
                        "confidence": 0.5 # Plausible
                    })
                
                # Also suggest just raw string as fallback
                cands.append({
                    "value": [cleaned],
                    "confidence": 0.3 # Weak
                })
                
                suggestions["authors"] = cands

    # 2. Title Remediation
    # 2. Title Remediation
    if "title" not in s2_fields or not s2_fields["title"].get("value"):
        # Heuristic: Text between Year and Journal/Publisher
        year_match = re.search(r"\(?((?:19|20)\d{2})\)?", raw_ref)
        if year_match:
            start = year_match.end()
            # Try to find end delimiters: Journal name often italicized or followed by Vol/Issue
            # We don't have italics in raw string. 
            # Look for common boundaries.
            
            # For Journal: stop at "Vol", number, or known journal name
            # For Book: stop at Publisher keywords or end
            
            rest = raw_ref[start:].strip(" .,")
            
            # Rough guess: take first significant chunk
            # Split by dot or question mark
            chunks = re.split(r"[.?]\s", rest)
            if chunks:
                guess = chunks[0].strip()
                if len(guess) > 5:
                    suggestions["title"] = [{
                        "value": guess,
                        "confidence": 0.4 # Plausible guess
                    }]

    # 3. Publisher/Organisation Remediation
    # 3. Publisher/Organisation Remediation
    if ref_type == "book":
         if "publisher" not in s2_fields or not s2_fields["publisher"].get("value"):
             # Look for keywords
             keywords = ["Press", "Wiley", "Springer", "Routledge", "Sage", "Macmillan", "Oxford", "Cambridge"]
             found = []
             for kw in keywords:
                 if kw in raw_ref:
                     # Attempt to grab surrounding context (e.g. "Oxford University Press")
                     # Regex: (Words) kw (Words)
                     # Simple: just suggest the keyword phrase match if simple
                     match = re.search(fr"\b([A-Z][a-z]+\s+)?{kw}(\s+[A-Z][a-z]+)?\b", raw_ref)
                     if match:
                         found.append(match.group(0))
             
             if found:
                 suggestions["publisher"] = [{"value": f, "confidence": 0.6} for f in set(found)]

    elif ref_type == "website":
        if "organisation" not in s2_fields or not s2_fields["organisation"].get("value"):
             # Suggest domain from URL if available
             s2_url = s2_fields.get("url", {}).get("value")
             if s2_url:
                 # Extract domain
                 domain_match = re.search(r"https?://(?:www\.)?([^/]+)", s2_url)
                 if domain_match:
                     dom = domain_match.group(1)
                     suggestions["organisation"] = [{
                         "value": dom, 
                         "confidence": 0.5
                     }]
             
             # Or look for "Available at: ..." context
             avail_match = re.search(r"Available at:", raw_ref, re.IGNORECASE)
             if avail_match:
                  # Text before "Available at" might contain org
                  # But extremely noisy.
                  pass

    # Calculate Overall Confidence
    # Max of any suggestion confidence, capped at 0.7
    max_conf = 0.0
    for field, items in suggestions.items():
        for item in items:
            max_conf = max(max_conf, item["confidence"])
            
    # Safety Cap
    max_conf = min(max_conf, 0.7)

    return {
        "suggested_fields": suggestions,
        "overall_confidence": max_conf,
        "requires_review": True, # NON-NEGOTIABLE
        "notes": ["Remediation applied via Stage 3 heuristics."] if suggestions else ["No remediation candidates found."]
    }

# --- EXAMPLES ---
if __name__ == "__main__":
    
    # Example 1: Partial Journal -> Suggest Authors
    # Stage 2 failed authors due to messiness layout
    ex1 = {
        "raw_reference": "Smith J and Doe A (2020) Bad formatting...",
        "reference_type": "journal",
        "stage2_output": {
            "extraction_status": "partial",
            "fields": {
                "year": {"value": 2020, "confidence": 0.95}, 
                "authors": {"value": None, "confidence": 0.0}
            }
        }
    }
    
    # Example 2: Failed Book -> Suggest Title/Publisher
    ex2 = {
        "raw_reference": "Unknown. (2019). The Big Book of Logic. Oxford University Press.",
        "reference_type": "book",
        "stage2_output": {
            "extraction_status": "failed",
            "fields": {
                 "year": {"value": 2019, "confidence": 0.95},
                 "publisher": {"value": None, "confidence": 0.0}
            }
        }
    }
    
    # Example 3: Partial Website -> Suggest Organisation
    ex3 = {
        "raw_reference": "BBC News (2021) Local Election Results. Available at: https://www.bbc.co.uk/news/...",
        "reference_type": "website",
        "stage2_output": {
            "extraction_status": "partial",
            "fields": {
                "url": {"value": "https://www.bbc.co.uk/news/...", "confidence": 0.95},
                "organisation": {"value": None, "confidence": 0.0}
            }
        }
    }

    # Example 4: Complete Extraction -> Should Skip
    ex4 = {
        "raw_reference": "Perfect Reference",
        "reference_type": "journal",
        "stage2_output": {
            "extraction_status": "complete",
            "fields": {"year": {"value": 2021}}
        }
    }
    
    print("--- Stage 3 Remediation Examples ---\n")
    
    for i, ex in enumerate([ex1, ex2, ex3, ex4], 1):
        print(f"Example {i} Input:")
        # print(json.dumps(ex, indent=2))
        print(f"Raw: {ex['raw_reference']}")
        print(f"Status: {ex['stage2_output']['extraction_status']}")
        
        result = remediate_reference(ex)
        
        print("Output:")
        print(json.dumps(result, indent=2))
        print("-" * 40)
