
import logging
from src.reference_manager import ReferenceManager

# Configure logging to see filter decisions
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

def test_noise_filtering():
    manager = ReferenceManager()
    
    # Test 1: Generic query that might pull irrelevant fuzzy matches
    print("\n--- Test 1: 'Foundation Mathematics' ---")
    results = manager.search_works("Foundation Mathematics", limit=10)
    print(f"Returned {len(results)} results.")
    for r in results:
        print(f"  [{r.confidence_score:.2f}] {r.title} ({r.source})")
        
    # Test 2: Author search with potential noise
    print("\n--- Test 2: Author 'Stenford Ruvinga' ---")
    results = manager.search_author_works("Stenford Ruvinga")
    print(f"Returned {len(results)} results.")
    for r in results:
        conf = getattr(r, 'confidence_score', 0.0)
        print(f"  [{conf:.2f}] {r.title} ({r.source})")
        
    # Test 3: Nonsense query
    print("\n--- Test 3: Nonsense query 'sdfsdfwefwe' ---")
    results = manager.search_works("sdfsdfwefwe", limit=5)
    print(f"Returned {len(results)} results.")
    for r in results:
        print(f"  [{r.confidence_score:.2f}] {r.title} ({r.source})")

if __name__ == "__main__":
    test_noise_filtering()
