from src.reference_manager import ReferenceManager
from src.models import Publication
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

rm = ReferenceManager()

# Simulate two results for the same book
# 1. CrossRef result (Good source score, but missing URL/ISBN)
p1 = Publication(
    title="Tambaoga mwanangu",
    authors=["Kuimba, Giles"],
    year="1968",
    source="crossref", # Higher weight traditionally
    pub_type="book",
    journal="", publisher="", location="", volume="", issue="", pages="", doi="", isbn="", url=""
)

# 2. Google Books result (Lower source score, but HAS URL/ISBN)
p2 = Publication(
    title="Tambaoga mwanangu",
    authors=["Giles Kuimba"],
    year="1968",
    source="google_books",
    pub_type="book",
    journal="", publisher="Longman", location="", volume="", issue="", pages="119", doi="", 
    isbn="9780582612389", 
    url="http://google.com/books/view"
)

print("\n--- Testing Deduplication Merge ---")
# Pass both. p1 is first, so it's the "existing" one in seen_titles.
# p2 comes second. It should be detected as duplicate, BUT its metadata merged into p1.
results = [p1, p2]
deduped = rm._deduplicate_results(results)

print(f"Input count: {len(results)}")
print(f"Output count: {len(deduped)}")

final = deduped[0]
print(f"Final Title: {final.title}")
print(f"Final Source: {final.source}") # Should be crossref (p1)
print(f"Final URL: {final.url}")       # Should be from p2!
print(f"Final ISBN: {final.isbn}")     # Should be from p2!

if final.url == "http://google.com/books/view":
    print("✅ SUCCESS: URL merged from duplicate!")
else:
    print("❌ FAILURE: URL lost!")
