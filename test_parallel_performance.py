"""
Performance test script for parallel vs sequential search.
Measures speed improvements from parallel architecture.
"""
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.reference_manager import ReferenceManager

def test_search_performance():
    """Compare parallel vs sequential search performance."""
    print("=" * 70)
    print("Parallel Search Performance Test")
    print("=" * 70)
    
    # Test queries
    test_queries = [
        "machine learning neural networks",
        "COVID-19 vaccine efficacy",
        "quantum computing algorithms",
        "climate change global warming",
        "CRISPR gene editing"
    ]
    
    manager = ReferenceManager()
    
    # Clear cache to ensure fair comparison
    manager.cache = {}
    
    print("\n### Testing Sequential Search (Old Method)")
    sequential_times = []
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        start = time.time()
        result = manager.search_single_work(query, use_parallel=False)
        elapsed = time.time() - start
        sequential_times.append(elapsed)
        
        if result:
            print(f"  [OK] Found in {elapsed:.2f}s: {result.title[:60]}...")
            print(f"  Source: {result.source}")
        else:
            print(f"  [SKIP] No result in {elapsed:.2f}s")
    
    # Clear cache again
    manager.cache = {}
    
    print("\n" + "=" * 70)
    print("### Testing Parallel Search (New Method)")
    parallel_times = []
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        start = time.time()
        result = manager.search_single_work(query, use_parallel=True)
        elapsed = time.time() - start
        parallel_times.append(elapsed)
        
        if result:
            print(f"  [OK] Found in {elapsed:.2f}s: {result.title[:60]}...")
            print(f"  Source: {result.source}")
        else:
            print(f"  [SKIP] No result in {elapsed:.2f}s")
    
    # Calculate statistics
    print("\n" + "=" * 70)
    print("### Performance Summary")
    print("=" * 70)
    
    avg_sequential = sum(sequential_times) / len(sequential_times)
    avg_parallel = sum(parallel_times) / len(parallel_times)
    speedup = avg_sequential / avg_parallel if avg_parallel > 0 else 0
    
    print(f"\nSequential Search:")
    print(f"  Average: {avg_sequential:.2f}s")
    print(f"  Min: {min(sequential_times):.2f}s")
    print(f"  Max: {max(sequential_times):.2f}s")
    
    print(f"\nParallel Search:")
    print(f"  Average: {avg_parallel:.2f}s")
    print(f"  Min: {min(parallel_times):.2f}s")
    print(f"  Max: {max(parallel_times):.2f}s")
    
    print(f"\nPerformance Improvement:")
    print(f"  Speedup: {speedup:.2f}x faster")
    print(f"  Time saved: {(avg_sequential - avg_parallel):.2f}s per search")
    
    if speedup >= 3.0:
        print(f"  [SUCCESS] Target exceeded! (>3x)")
    elif speedup >= 2.0:
        print(f"  [GOOD] Significant improvement (>2x)")
    else:
        print(f"  [WARN] Below target (<2x)")

def test_result_quality():
    """Verify parallel search returns correct results."""
    print("\n" + "=" * 70)
    print("### Result Quality Test")
    print("=" * 70)
    
    manager = ReferenceManager()
    manager.cache = {}
    
    # Test known papers
    test_cases = [
        ("Attention is all you need", "transformer"),
        ("ImageNet classification", "AlexNet"),
    ]
    
    for query, expected_keyword in test_cases:
        print(f"\nQuery: {query}")
        result = manager.search_single_work(query, use_parallel=True)
        
        if result:
            title_match = expected_keyword.lower() in result.title.lower()
            print(f"  Title: {result.title}")
            print(f"  Keyword '{expected_keyword}' found: {title_match}")
            print(f"  Authors: {', '.join(result.authors[:3])}")
            print(f"  Year: {result.year}")
            print(f"  [{'OK' if title_match else 'WARN'}]")
        else:
            print(f"  [FAIL] No result found")

if __name__ == "__main__":
    try:
        test_search_performance()
        test_result_quality()
        
        print("\n" + "=" * 70)
        print("[SUCCESS] Performance testing complete!")
        print("=" * 70)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
