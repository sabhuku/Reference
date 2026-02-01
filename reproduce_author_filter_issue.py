from src.referencing import referencing
import logging

logging.basicConfig(level=logging.INFO)

def test_author_filter():
    query = "Smith"
    year_from = 2023
    year_to = 2024
    
    print(f"Searching for author '{query}' with Years: {year_from}-{year_to}")
    
    # Try passing filters to lookup_author_works
    try:
        results = referencing.lookup_author_works(
            query, 
            year_from=year_from, 
            year_to=year_to
        )
        
        print(f"Found {len(results)} results.")
        
        if not results:
            print("No results found. This might be correct if no pubs match the year.")
            
        for i, res in enumerate(results[:5]):
            year = res.get('year')
            print(f"[{i+1}] Year: {year} | Title: {res.get('title')}")
            
            # Check validity
            try:
                import re
                match = re.search(r'\d{4}', str(year))
                if match:
                    y = int(match.group(0))
                    if y < year_from or y > year_to:
                         print(f"    >>> FAIL: Year {y} is outside {year_from}-{year_to}")
                    else:
                         print(f"    >>> PASS: Year {y} is within range")
            except:
                pass
                
    except TypeError as e:
        print(f"FAILED to pass filters: {e}")
        print("FIX REQUIRED: lookup_author_works still does not accept filters.")

if __name__ == "__main__":
    test_author_filter()
