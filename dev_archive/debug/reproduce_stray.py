from src.reference_manager import ReferenceManager
import logging
import sys

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO)

rm = ReferenceManager()
query = "Foundation Mathematics"
print(f"Searching for: {query}")
results = rm.search_works(query)

print(f"\nFound {len(results)} results:")
for i, r in enumerate(results):
    # The reference manager only populates it for the top one usually,
    # but let's see if we can get it or just print title.
    score = getattr(r, 'confidence_score', 0) * 121 # Approximate raw score
    print(f"[{r.source}] ({score:.1f}) {str(r.title)}")
    sys.stdout.flush()
