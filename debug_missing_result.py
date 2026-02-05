from src.reference_manager import ReferenceManager
import logging
import sys

# Configure logging to stdout with DEBUG level to see filtering decisions
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s: %(message)s',
    stream=sys.stdout
)

rm = ReferenceManager()
query = "tambaoga mwanangu"

print(f"\n{'='*50}")
print(f"TEST 1: General Mode Search for '{query}'")
print(f"{'='*50}")
results_gen = rm.search_works(query, limit=10, search_mode='general')

print(f"\n--- General Mode Results ({len(results_gen)}) ---")
for r in results_gen:
    print(f"Title: {r.title}")
    print(f"  Source: {r.source}")
    print(f"  Score: {r.confidence_score}")
    print(f"  URL: {r.url}")

print(f"\n{'='*50}")
print(f"TEST 2: Title Mode Search for '{query}'")
print(f"{'='*50}")
results_title = rm.search_works(query, limit=10, search_mode='title')

print(f"\n--- Title Mode Results ({len(results_title)}) ---")
for r in results_title:
    print(f"Title: {r.title}")
    print(f"  Source: {r.source}")
    print(f"  Score: {r.confidence_score}")
    print(f"  URL: {r.url}")
