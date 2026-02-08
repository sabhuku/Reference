"""
Test search quality improvements
"""
from src.reference_manager import ReferenceManager

# Initialize
rm = ReferenceManager()

# Test 1: "Let's do mathematics" - should return 0 results or only math-related
print("=" * 60)
print("Test 1: \"Let's do mathematics\"")
print("=" * 60)
results = rm.search_works("Let's do mathematics", limit=5)
print(f"Found {len(results)} results\n")
for i, r in enumerate(results):
    print(f"{i+1}. {r.title}")
    print(f"   Author: {r.authors}")
    print(f"   Year: {r.year}")
    print(f"   Score: {r.confidence_score:.2f}")
    print()

# Test 2: "Foundation Mathematics" - should return relevant math textbooks
print("=" * 60)
print("Test 2: \"Foundation Mathematics\"")
print("=" * 60)
results = rm.search_works("Foundation Mathematics", limit=5)
print(f"Found {len(results)} results\n")
for i, r in enumerate(results):
    print(f"{i+1}. {r.title}")
    print(f"   Author: {r.authors}")
    print(f"   Year: {r.year}")
    print(f"   Score: {r.confidence_score:.2f}")
    print()
