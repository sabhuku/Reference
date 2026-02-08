from src.reference_manager import ReferenceManager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

rm = ReferenceManager()
query = "Tambaoga mwanangu"

print(f"--- Searching for '{query}' to verify ISBN extraction ---")
results = rm.search_works(query, limit=5, search_mode='title')

found = False
for r in results:
    if "Tambaoga" in r.title:
        found = True
        print(f"Title: {r.title}")
        print(f"ISBN: {r.isbn}")
        print(f"Publisher: {r.publisher}")
        print(f"Source: {r.source}")
        
        if r.isbn:
            print("✅ ISBN successfully extracted!")
        else:
            print("❌ ISBN missing (check debug script raw output vs parser)")

if not found:
    print("❌ Book not found even with updated parser?")
