from src.reference_manager import ReferenceManager
from src.name_utils import guess_first_last_from_author_query, names_match
import logging

logging.basicConfig(level=logging.DEBUG)

def debug_missing_author():
    query = "ruvinga stenford"
    print(f"--- Debugging Query: '{query}' ---")
    
    # 1. Test Key Assumption: Name Parsing
    first, last = guess_first_last_from_author_query(query)
    print(f"Parsed Query -> First: '{first}', Last: '{last}'")
    
    # 2. Simulate Matching against known real author "Ruvinga, Stenford"
    # CrossRef usually returns family="Ruvinga", given="Stenford"
    real_family = "Ruvinga"
    real_given = "Stenford"
    
    print(f"\nComparing against Real Author -> Family: '{real_family}', Given: '{real_given}'")
    match = names_match(first, last, real_given, real_family)
    print(f"Match Result (Query vs Real): {match}")
    
    if not match:
        print(">>> CAUSE FOUND: The parsed query does not match the actual author name structure.")
        print("    likely due to First/Last name checking order.")

    # 3. Run Actual Search (to see API results and filtering in action)
    print("\n--- Running Manager Search ---")
    mgr = ReferenceManager()
    
    # Force clear cache
    for k in list(mgr.cache.keys()):
        if "ruvinga" in k.lower():
            del mgr.cache[k]
            
    try:
        results = mgr.search_author_works(query)
        print(f"Found {len(results)} results.")
        for res in results:
            print(f" - {res.title} (Authors: {res.authors})")
    except Exception as e:
        print(f"Search failed: {e}")

if __name__ == "__main__":
    debug_missing_author()
