from src.reference_manager import ReferenceManager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

rm = ReferenceManager()
query = "Tambaoga mwanangu"

print(f"--- Searching for '{query}' to verify Metadata extraction (ISBN + URL) ---")
results = rm.search_works(query, limit=5, search_mode='title')

found = False
for r in results:
    if "Tambaoga" in r.title:
        found = True
        print(f"Title: {r.title}")
        print(f"ISBN: {r.isbn}")
        print(f"URL: {r.url}")
        print(f"Source: {r.source}")
        
        if r.url and "http" in r.url:
            print("✅ URL successfully extracted!")
        else:
            print("❌ URL missing")

if not found:
    print("❌ Book not found")
