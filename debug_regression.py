import sys
import os
import logging

# Set up path
sys.path.append(os.getcwd())

from src.reference_manager import ReferenceManager

# Configure logging to see debug output from ReferenceManager
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

def debug_regression():
    print("Initializing ReferenceManager...")
    manager = ReferenceManager()
    
    query = "use of the lstm network to identify queenlessness in honeybee colonies"
    print(f"\nSearching for: '{query}'")
    
    # 1. Search with 'general' mode first to see if it appears at all
    print("\n--- TEST 1: General Search ---")
    results_gen = manager.search_works(query, search_mode='general')
    print(f"General Search Found: {len(results_gen)}")
    for r in results_gen:
        print(f" - [{r.confidence_score:.2f}] {r.title}")

    # 2. Search with 'title' mode (strict)
    print("\n--- TEST 2: Title Search ---")
    results_title = manager.search_works(query, search_mode='title')
    print(f"Title Search Found: {len(results_title)}")
    for r in results_title:
        print(f" - [{r.confidence_score:.2f}] {r.title}")

if __name__ == "__main__":
    debug_regression()
