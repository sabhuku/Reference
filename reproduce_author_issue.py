from src.reference_manager import ReferenceManager
import logging

logging.basicConfig(level=logging.INFO)

def test_author_accuracy():
    mgr = ReferenceManager()
    query = "Ruvinga S"
    print(f"Searching for author: '{query}'")
    print(f"Cache location: {mgr.config.CACHE_FILE}")
    print(f"Cache size before clear: {len(mgr.cache)}")
    
    # FORCE CLEAR CACHE to test filtering logic
    if f"author:{query}" in mgr.cache:
        del mgr.cache[f"author:{query}"]
    
    # We want to see results from each source independently to identify the culprit
    # But ReferenceManager combines them. Let's call them directly if possible, 
    # or just analyze the combined output source-by-source.
    
    results = mgr.search_author_works(query)
    
    print(f"Found {len(results)} total results.")
    
    print("\n--- Analyze Authors ---")
    for i, res in enumerate(results):
        # res might be a dict now if cached, need to handle that
        # But for reproduction we are running fresh?
        # If cache exists, it might load old bad results. 
        # But let's assume valid access.
        
        authors = res.get('authors', []) if isinstance(res, dict) else res.authors
        source = res.get('source', 'unknown') if isinstance(res, dict) else res.source
        title = res.get('title', 'No Title') if isinstance(res, dict) else res.title
        
        try:
            print(f"[{i+1}] Source: {source} | Authors: {authors}")
        except UnicodeEncodeError:
            print(f"[{i+1}] Source: {source} | Authors: [Encoding Error]")
        
        # Check if "Ruvinga" is in authors
        has_ruvinga = False
        for a in authors:
            if "ruvinga" in a.lower():
                has_ruvinga = True
                break
        
        if not has_ruvinga:
             print(f"    >>> PROBLEM: 'Ruvinga' NOT FOUND in authors for: {title}")

if __name__ == "__main__":
    test_author_accuracy()
