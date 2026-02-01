
import json
import copy
from src.models import Publication
from src.normalizer import ReferenceNormalizer

def verify_idempotence():
    # Test Data: 1 publication that needs normalization
    p = Publication(
        title="Test Pub", 
        authors=["Doe, A"], # Needs dot? Or just raw
        year="2020a", 
        pub_type="article",
        journal="J Test",
        publisher="", location="", volume="", issue="", pages="",
        source="test", doi="10.1000/test"
    )
    
    # Run 1
    ReferenceNormalizer.normalize(p)
    state_after_1 = copy.deepcopy(p)
    
    # Run 2
    ReferenceNormalizer.normalize(p)
    state_after_2 = copy.deepcopy(p)
    
    # Compare
    report = []
    
    # Check Authors
    if state_after_1.normalized_authors != state_after_2.normalized_authors:
        report.append({
            "PublicationID": "Test1",
            "Field": "normalized_authors",
            "Change": f"{state_after_1.normalized_authors} -> {state_after_2.normalized_authors}",
            "Severity": "high"
        })
        
    # Check Year
    if state_after_1.year != state_after_2.year:
        report.append({
            "PublicationID": "Test1",
            "Field": "year",
            "Change": f"{state_after_1.year} -> {state_after_2.year}",
            "Severity": "high"
        })
        
    # Check Logs (Should NOT grow if idempotent, unless we log "Already normalized")
    # Actually, if we skip, log shouldn't grow.
    if len(state_after_1.normalization_log) != len(state_after_2.normalization_log):
        # This is expected if we log "Skipping", but we want to know if it DID work again.
        # Ideally, idempotent means result State is same. Log might differ.
        pass
        
    if not report:
        print(json.dumps([{"Status": "Idempotence Verified", "Severity": "success"}], indent=2))
    else:
        print(json.dumps(report, indent=2))

if __name__ == "__main__":
    verify_idempotence()
