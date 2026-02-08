
import json
import difflib
import sys
import os

def load_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {path}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON {path}: {e}")
        return None

def compare_lists(l1, l2):
    """Compare two lists of strings order-insensitively for basic equality, 
    or order-sensitively if needed. Authors are usually order-sensitive."""
    if l1 == l2:
        return True
    return False

def categorize_discrepancy(field, old_val, new_val):
    severity = "info"
    note = ""
    
    if field == "authors":
        # Author Count Mismatch
        if len(old_val) != len(new_val):
            return "high", f"Author count changed: {len(old_val)} -> {len(new_val)}"
        
        # Check normalization changes
        diffs = []
        for o, n in zip(old_val, new_val):
            if o != n:
                if o.replace('.', '') == n.replace('.', ''):
                    diffs.append("Punctuation change")
                    severity = "low"
                elif "," in n and "," not in o:
                    diffs.append("Normalization format applied")
                    severity = "moderate" # Expected improvement
                else:
                    diffs.append("Name content changed")
                    severity = "high"
        note = "; ".join(diffs)
            
    elif field == "year":
        if not old_val and new_val:
            severity = "moderate"
            note = "Year extracted where previously missing"
        elif old_val and not new_val:
            severity = "high"
            note = "Year lost"
        elif old_val.replace('a','').replace('b','') == new_val.replace('a','').replace('b',''):
             severity = "moderate"
             note = "Suffix handling changed"
        else:
            severity = "high"
            note = f"Year value mismatch: {old_val} -> {new_val}"
            
    elif field == "compliance_score":
        # Check float difference
        try:
            o_score = float(old_val)
            n_score = float(new_val)
            if abs(o_score - n_score) > 5.0:
                severity = "high"
                note = "Significant score swing > 5 pts"
            elif abs(o_score - n_score) > 0.1:
                severity = "moderate"
                note = "Minor score adjustment"
            else:
                severity = "low"
                note = "Floating point noise"
        except:
             severity = "high"
             note = "Score type mismatch"

    elif field == "violations":
        # Compare count or sets
        o_ids = set(v.get('rule_id') for v in old_val) if isinstance(old_val, list) else set()
        n_ids = set(v.get('rule_id') for v in new_val) if isinstance(new_val, list) else set()
        
        added = n_ids - o_ids
        removed = o_ids - n_ids
        
        if added or removed:
            severity = "moderate"
            note = f"Violations Changed: +{list(added)}, -{list(removed)}"
        else:
            severity = "low"
            note = "Violation metadata changed"

    else:
        severity = "moderate"
        note = f"Value change: '{old_val}' -> '{new_val}'"

    return severity, note

def compare_publications(baseline, enhanced):
    report = []
    
    # Map by ID if possible, assuming list of dicts with 'id' or 'title'
    # Fallback to index matching if purely sequential
    
    base_map = {p.get('id', i): p for i, p in enumerate(baseline)}
    enh_map = {p.get('id', i): p for i, p in enumerate(enhanced)}
    
    all_keys = set(base_map.keys()) | set(enh_map.keys())
    
    for key in all_keys:
        if key not in base_map:
            report.append({
                "PublicationID": str(key),
                "Field": "publication",
                "Discrepancy": "New publication detected",
                "Severity": "high",
                "Notes": "Enhanced version found a pub missed by baseline"
            })
            continue
            
        if key not in enh_map:
            report.append({
                "PublicationID": str(key),
                "Field": "publication",
                "Discrepancy": "Publication lost",
                "Severity": "high",
                "Notes": "Enhanced version missed a pub found by baseline"
            })
            continue
            
        b = base_map[key]
        e = enh_map[key]
        
        # Fields to compare
        fields = ["authors", "year", "pub_type", "title", "violations", "compliance_score"]
        
        for f in fields:
            val_b = b.get(f)
            val_e = e.get(f)
            
            # Normalization might make fields distinct objects (lists), equality check handles it
            if val_b != val_e:
                sev, note = categorize_discrepancy(f, val_b, val_e)
                report.append({
                    "PublicationID": str(key),
                    "Field": f,
                    "Discrepancy": f"{f} changed",
                    "Severity": sev,
                    "Notes": note,
                    "OldValue": str(val_b)[:50],
                    "NewValue": str(val_e)[:50]
                })
                
    return report

def main():
    if len(sys.argv) < 3:
        print("Usage: python compare_outputs.py baseline_outputs.json enhanced_outputs.json")
        # Generates dummy test files if not present for demonstration
        if not os.path.exists('baseline_outputs.json'):
             print("Creating dummy baseline_outputs.json...")
             with open('baseline_outputs.json', 'w') as f:
                 json.dump([{
                     "id": "1", "title": "Test Paper", "authors": ["Doe, A"], "year": "2020", 
                     "pub_type": "article", "compliance_score": 80.0, "violations": []
                 }], f)
        if not os.path.exists('enhanced_outputs.json'):
             print("Creating dummy enhanced_outputs.json...")
             with open('enhanced_outputs.json', 'w') as f:
                 json.dump([{
                     "id": "1", "title": "Test Paper", "authors": ["Doe, A."], "year": "2020a", 
                     "pub_type": "article", "compliance_score": 85.0, "violations": []
                 }], f)
        # re-check logic to run normally if dummy created
        # return

    path_b = sys.argv[1] if len(sys.argv) > 1 else 'baseline_outputs.json'
    path_e = sys.argv[2] if len(sys.argv) > 2 else 'enhanced_outputs.json'
    
    base = load_json(path_b)
    enh = load_json(path_e)
    
    if base is None or enh is None:
        return

    report = compare_publications(base, enh)
    
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
