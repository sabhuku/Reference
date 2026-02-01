
import json
import copy
from src.reference_manager import ReferenceManager
from src.style.harvard_checker import HarvardStyleChecker
from src.style.report_generator import HarvardComplianceReportGenerator
from src.models import Publication

def create_dataset():
    pubs = []
    
    # Group A: Identical (Should merge to 1)
    for i in range(20):
        p = Publication(title="Unique Title A", authors=["Smith"], year="2020", doi="10.1000/A", source="crossref", pub_type="article", journal="", publisher="", location="", volume="", issue="", pages="")
        p.violations = []
        pubs.append(p)
        
    # Group B: Unique (Should be 20)
    for i in range(20):
        p = Publication(title=f"Unique Title B{i}", authors=["Doe"], year="2020", doi=f"10.1000/B{i}", source="crossref", pub_type="article", journal="", publisher="", location="", volume="", issue="", pages="")
        p.violations = []
        pubs.append(p)
        
    # Group C: Fuzzy (Sim > 90%) (Should merge)
    for i in range(10):
        p1 = Publication(title="Machine Learning in Health", authors=["Lee"], year="2021", doi=f"10.1000/C{i}", source="crossref", pub_type="article", journal="", publisher="", location="", volume="", issue="", pages="")
        p1.violations = []
        pubs.append(p1)
        
        p2 = Publication(title="Machine Learning in Health.", authors=["Lee"], year="2021", doi=f"10.1000/C{i}_dup", source="crossref", pub_type="article", journal="", publisher="", location="", volume="", issue="", pages="")
        p2.violations = []
        pubs.append(p2)

    return pubs

def main():
    mgr = ReferenceManager()
    checker = HarvardStyleChecker()
    generator = HarvardComplianceReportGenerator()
    
    base_pubs = create_dataset()
    
    # Run 1
    input1 = copy.deepcopy(base_pubs)
    deduped1 = mgr._deduplicate_results(input1)
    checker.check_publications(deduped1)
    # Ensure scores are calculated
    for p in deduped1:
         p.compliance_score = max(0.0, 100.0 - sum(v.get('penalty', 0) for v in p.violations))
    scores1 = {p.doi: p.compliance_score for p in deduped1}
    
    # Run 2
    input2 = copy.deepcopy(base_pubs)
    deduped2 = mgr._deduplicate_results(input2)
    checker.check_publications(deduped2)
    for p in deduped2:
         p.compliance_score = max(0.0, 100.0 - sum(v.get('penalty', 0) for v in p.violations))
    scores2 = {p.doi: p.compliance_score for p in deduped2}
    
    findings = []
    
    # 1. Scoring Consistency
    for doi, score in scores1.items():
        if doi in scores2:
            if abs(score - scores2[doi]) > 0.01:
                 findings.append({
                     "PublicationID": str(doi),
                     "Issue": "Score varies across runs",
                     "Frequency": "High",
                     "Recommendation": "Fix StyleChecker non-determinism"
                 })
        else:
             findings.append({
                 "PublicationID": str(doi),
                 "Issue": "Publication missing in Run 2",
                 "Frequency": "High",
                 "Recommendation": "Fix Deduplication instability"
             })
             
    # 2. Merge Verification
    count_A = len([p for p in deduped1 if "10.1000/A" in p.doi])
    if count_A > 1:
        findings.append({
            "PublicationID": "Group A",
            "Issue": "Identical duplicates not merged",
            "Frequency": "High",
            "Recommendation": "Check DOI deduplication logic"
        })
        
    count_C = len([p for p in deduped1 if "10.1000/C" in p.doi])
    # Expect 10 merged results. If 20, merge failed.
    if count_C > 10:
         findings.append({
             "PublicationID": "Group C",
             "Issue": "Fuzzy duplicates not merged",
             "Frequency": "Moderate",
             "Recommendation": f"Raise fuzz threshold? Count={count_C}"
         })
    
    if not findings:
        print(json.dumps([{"Status": "Consistent", "Analysis": f"Group A merged to {count_A} (Expected 1). Group C merged to {count_C} (Expected 10ish)"}], indent=2))
    else:
        print(json.dumps(findings, indent=2))

if __name__ == "__main__":
    main()
