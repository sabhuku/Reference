import sys
import os

# Set up path
sys.path.append(os.getcwd())

from src.reference_manager import ReferenceManager
import logging

# Configure basic logging to stderr
logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

def test_search():
    print("Initializing ReferenceManager...")
    try:
        manager = ReferenceManager()
    except Exception as e:
        print(f"Failed to init manager: {e}")
        return

    query = "Foundation Mathematics" # Term mentioned in earlier summary as problematic
    print(f"Searching for: '{query}' (mode='title')")
    
    try:
        results = manager.search_works(query, search_mode='title')
        print(f"Success! Found {len(results)} results.")
        for r in results:
            print(f"- {r.title} ({r.doi})")
    except Exception as e:
        print("CRITICAL EXCEPTION CAUGHT:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_search()
