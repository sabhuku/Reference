"""
Test phrase-aware keyword matching with educational phrase filtering
"""
from src.reference_manager import ReferenceManager

# Initialize
rm = ReferenceManager()

# Test: "A'level Biology" - should only return A-level education results
print("=" * 60)
print("Test: \"A'level Biology\"")
print("=" * 60)
results = rm.search_works("A'level Biology", limit=10)
print(f"Found {len(results)} results\n")
for i, r in enumerate(results):
    print(f"{i+1}. {r.title}")
    print(f"   Year: {r.year}")
    print(f"   Score: {r.confidence_score:.2f}")
    print()
