"""
Test context-aware keyword filtering with proximity scoring
"""
from src.reference_manager import ReferenceManager

# Initialize
rm = ReferenceManager()

# Test: "A'level Mathematics" - should prioritize results with keywords close together
print("=" * 60)
print("Test: \"A'level Mathematics\"")
print("=" * 60)
results = rm.search_works("A'level Mathematics", limit=10)
print(f"Found {len(results)} results\n")
for i, r in enumerate(results):
    print(f"{i+1}. {r.title}")
    print(f"   Year: {r.year}")
    print(f"   Score: {r.confidence_score:.2f}")
    if hasattr(r, 'selection_details') and r.selection_details:
        criteria = r.selection_details.get('criteria', {})
        if 'keyword_proximity' in criteria:
            print(f"   ✓ Proximity bonus: {criteria['keyword_proximity']}")
    print()
