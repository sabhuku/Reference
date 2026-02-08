"""
Quick test script for PubMed integration.
Tests single work search and author search with medical queries.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.api import PubMedAPI

def test_pubmed_single():
    """Test single work search."""
    print("=" * 70)
    print("Testing PubMed Single Work Search")
    print("=" * 70)
    
    pubmed = PubMedAPI()
    
    test_queries = [
        "COVID-19 vaccine efficacy",
        "CRISPR gene editing",
        "Alzheimer's disease treatment",
    ]
    
    for query in test_queries:
        print(f"\n### Query: {query}")
        result = pubmed.search_single(query)
        
        if result:
            print(f"[OK] Found: {result.title}")
            print(f"   Authors: {', '.join(result.authors[:3])}{'...' if len(result.authors) > 3 else ''}")
            print(f"   Year: {result.year}")
            print(f"   Journal: {result.journal}")
            print(f"   DOI: {result.doi or 'N/A'}")
            print(f"   Source: {result.source}")
        else:
            print(f"[FAIL] No results found")

def test_pubmed_author():
    """Test author search."""
    print("\n" + "=" * 70)
    print("Testing PubMed Author Search")
    print("=" * 70)
    
    pubmed = PubMedAPI()
    
    author = "Fauci AS"
    print(f"\n### Author: {author}")
    
    results = pubmed.search_author(author, max_results=5)
    
    if results:
        print(f"[OK] Found {len(results)} publications:")
        for i, pub in enumerate(results[:5], 1):
            print(f"   {i}. {pub.title[:70]}{'...' if len(pub.title) > 70 else ''}")
            print(f"      Year: {pub.year}, Journal: {pub.journal}")
    else:
        print(f"[FAIL] No results found")

def test_integration():
    """Test integration with ReferenceManager."""
    print("\n" + "=" * 70)
    print("Testing ReferenceManager Integration")
    print("=" * 70)
    
    from src.reference_manager import ReferenceManager
    
    manager = ReferenceManager()
    
    query = "diabetes mellitus treatment"
    print(f"\n### Query: {query}")
    
    result = manager.search_single_work(query)
    
    if result:
        print(f"[OK] Found: {result.title}")
        print(f"   Source: {result.source}")
        print(f"   Authors: {', '.join(result.authors[:3])}{'...' if len(result.authors) > 3 else ''}")
        print(f"   Year: {result.year}")
    else:
        print(f"[FAIL] No results found")

if __name__ == "__main__":
    try:
        test_pubmed_single()
        test_pubmed_author()
        test_integration()
        
        print("\n" + "=" * 70)
        print("[SUCCESS] All tests completed!")
        print("=" * 70)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()

