import requests
import json
import os

# Config from existing setup if possible, otherwise use public access
# (Google Books works without key for rate-limited public data)

def debug_google_books_raw(query):
    print(f"--- Querying Google Books for: {query} ---")
    url = "https://www.googleapis.com/books/v1/volumes"
    params = {
        "q": query,
        "maxResults": 3
    }
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        items = data.get("items", [])
        print(f"Found {len(items)} items.\n")
        
        for i, item in enumerate(items):
            v_info = item.get("volumeInfo", {})
            print(f"Item #{i+1}:")
            print(f"  Title: {v_info.get('title')}")
            print(f"  Authors: {v_info.get('authors')}")
            print(f"  Publisher: {v_info.get('publisher')}")
            print(f"  PublishedDate: {v_info.get('publishedDate')}")
            
            # Check for industryIdentifiers (ISBNs)
            print(f"  IndustryIdentifiers: {v_info.get('industryIdentifiers')}")
            
            # Check for generic selfLink or infoLink
            print(f"  InfoLink: {v_info.get('infoLink')}")
            
            # Print entire raw volumeInfo for deep inspection
            print("  [RAW volumeInfo DUMP below]")
            print(json.dumps(v_info, indent=2))
            print("-" * 40)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    queries = [
        "Tambaoga mwanangu",
        "intitle:Tambaoga mwanangu",
        "Tambaoga mwanangu+inauthor:Kuimba"
    ]
    for q in queries:
        debug_google_books_raw(q)
