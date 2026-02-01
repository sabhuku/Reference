import sys
import os

# mimics main.py setup
src_path = os.path.abspath(os.path.join(os.getcwd(), 'src'))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from src.referencing import referencing
import logging

# Set up logging to catch the error detail
logging.basicConfig(level=logging.ERROR)

from src.referencing import referencing
import logging

logging.basicConfig(level=logging.ERROR)

def test_author_search():
    print("Searching for author 'Smith' via referencing module...")
    try:
        results = referencing.lookup_author_works("Smith")
        print(f"Found {len(results)} results.")
        if results:
             print(f"Result 0 title: {results[0].get('title')}")
    except Exception as e:
        print(f"CAUGHT EXCEPTION: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_author_search()
