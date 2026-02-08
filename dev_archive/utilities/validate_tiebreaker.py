
import json
import random
from collections import defaultdict
from src.models import Publication
from src.reference_manager import ReferenceManager

# Mocking the scoring result structure expected by _rank_results if needed, 
# but _rank_results takes `(pub, source)` and re-scores? 
# No, `_rank_results` takes `results: List[Tuple[Publication, str]]` (pub, source_name).
# It calculates score internally.
# To force equal scores, we need pubs that look identical to the scorer.

def create_tied_publications():
    # Create 3 pubs that will score identically
    # Same source ('crossref' = 10 pts)
    # Same title match quality (Exact match = 100 pts)
    # Different metadata to test tie-breaker (Title string, DOI, Year)
    
    pubs = []
    
    # Pub A
    p1 = Publication(title="Analysis of AI", authors=["Smith"], year="2020", doi="10.1000/a", source="crossref",
                     pub_type="article", journal="", publisher="", location="", volume="", issue="", pages="")
    pubs.append((p1, "crossref"))
    
    # Pub B (Same title, later year)
    p2 = Publication(title="Analysis of AI", authors=["Smith"], year="2021", doi="10.1000/b", source="crossref",
                     pub_type="article", journal="", publisher="", location="", volume="", issue="", pages="")
    pubs.append((p2, "crossref"))
    
    # Pub C (Diff title, same year as A)
    p3 = Publication(title="Analysis of BI", authors=["Smith"], year="2020", doi="10.1000/c", source="crossref",
                     pub_type="article", journal="", publisher="", location="", volume="", issue="", pages="")
    pubs.append((p3, "crossref"))
    
    return pubs

def main():
    mgr = ReferenceManager()
    query = "Analysis of AI"
    
    tied_pubs = create_tied_publications()
    
    rank_stats = defaultdict(list)
    
    print("Simulating 100 ranking runs with shuffled input...")
    
    for i in range(100):
        # Shuffle input to simulate thread variance
        current_batch = list(tied_pubs)
        random.shuffle(current_batch)
        
        # Rank
        ranked = mgr._rank_results(current_batch, query)
        
        # Record positions
        for rank, pub in enumerate(ranked):
            # Identify by DOI
            rank_stats[pub.doi].append(rank + 1) # 1-based rank
            
    # Generate Report
    report = []
    for doi, ranks in rank_stats.items():
        unique_ranks = sorted(list(set(ranks)))
        
        # Determine recommendation
        if len(unique_ranks) > 1:
            rec = "Use DOI → title → year (Unstable)"
        else:
            rec = "No change needed (Stable)"
            
        # Find which pub this DOI belongs to for reporting ID
        # (Simplified)
        
        entry = {
            "PublicationDOI": doi,
            "ObservedRanks": unique_ranks, # Show unique ranks found
            "Variance": len(unique_ranks) > 1,
            "Recommendation": rec
        }
        report.append(entry)
        
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
