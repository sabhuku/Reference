"""
Test differentiation between Title and Keyword search modes.
"""
from src.reference_manager import ReferenceManager
import logging

# Configure logging to see dropped results
logging.basicConfig(level=logging.DEBUG)

rm = ReferenceManager()

query = "systems biology"

print(f"--- Testing Keyword Search for '{query}' ---")
results_general = rm.search_works(query, limit=5, search_mode='general')
print(f"Found {len(results_general)} results.")
for r in results_general:
    print(f"- {r.title} (Score: {r.confidence_score:.2f})")

print(f"\n--- Testing Strict Title Search for '{query}' ---")
results_title = rm.search_works(query, limit=5, search_mode='title')
print(f"Found {len(results_title)} results.")
for r in results_title:
    print(f"- {r.title} (Score: {r.confidence_score:.2f})")

# Test strictness: Search for a term unlikely to be in title if just keyword matching
query_strict = "introduction" 
# "introduction" is common in titles, maybe "recent advances"? 
# Let's try "implications" - often in abstract but not always in title.
# Or better: "comprehensive review" - common in title, but let's try something specific.
# "biochemical implications"

print(f"\n--- Testing Strictness: 'biochemical implications' ---")
print("General Mode:")
res_gen = rm.search_works("biochemical implications", limit=3, search_mode='general')
for r in res_gen:
    print(f"- {r.title}")

print("\nTitle Mode:")
res_title = rm.search_works("biochemical implications", limit=3, search_mode='title')
for r in res_title:
    print(f"- {r.title}")
