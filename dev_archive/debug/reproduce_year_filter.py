from src.reference_manager import ReferenceManager
import logging

logging.basicConfig(level=logging.INFO)

def test_year_filtering():
    mgr = ReferenceManager()
    query = "machine learning"
    year_from = 2023
    year_to = 2024
    
    print(f"Searching for '{query}' with Years: {year_from}-{year_to}")
    
    # Force clear cache for this query to test filtering
    if f"query:{query}" in mgr.cache:
        del mgr.cache[f"query:{query}"]
        
    # We need to manually construct the key usually used by search_works if we want to clear it?
    # search_works doesn't use a simple key for the whole search, it uses parallel_search.
    # parallel_search results are not cached as a whole list in the same way, 
    # but individual items might be? 
    # Actually, ReferenceManager doesn't seem to cache the *search results list* for `search_works` 
    # based on the filter params in the key. 
    # Wait, ReferenceManager.search_works calls parallel_search which builds results.
    # Does it cache?
    # Let's check the code.
    
    results = mgr.search_works(query, limit=10, year_from=year_from, year_to=year_to)
    
    print(f"Found {len(results)} results.")
    
    for i, res in enumerate(results):
        # Handle dict vs object
        year = res.get('year') if isinstance(res, dict) else res.year
        title = res.get('title') if isinstance(res, dict) else res.title
        
        print(f"[{i+1}] Year: {year} | Title: {title}")
        
        # Check validity
        try:
            import re
            match = re.search(r'\d{4}', str(year))
            if match:
                y = int(match.group(0))
                if y < year_from or y > year_to:
                     print(f"    >>> FAIL: Year {y} is outside {year_from}-{year_to}")
            else:
                print(f"    >>> FAIL: Could not parse year '{year}'")
        except:
             print(f"    >>> FAIL: Error parsing year '{year}'")

if __name__ == "__main__":
    test_year_filtering()
