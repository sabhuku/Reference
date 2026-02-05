
import time
import concurrent.futures
import statistics
import logging
from src.reference_manager import ReferenceManager

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def perform_search(manager, query):
    start_time = time.time()
    try:
        results = manager.search_works(query)
        duration = time.time() - start_time
        return duration, len(results), None
    except Exception as e:
        duration = time.time() - start_time
        return duration, 0, str(e)

def benchmark_search_concurrency(queries, max_workers_list=[1, 5, 10]):
    manager = ReferenceManager()
    
    # Warmup
    print("Warming up...")
    manager.search_works("test", limit=1)

    results_summary = {}

    for workers in max_workers_list:
        print(f"\nBenchmarking with {workers} concurrent workers...")
        latencies = []
        errors = 0
        
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_query = {executor.submit(perform_search, manager, q): q for q in queries}
            for future in concurrent.futures.as_completed(future_to_query):
                duration, count, error = future.result()
                latencies.append(duration)
                if error:
                    errors += 1
                    logging.error(f"Error for query '{future_to_query[future]}': {error}")
        
        total_time = time.time() - start_time
        
        avg_latency = statistics.mean(latencies) if latencies else 0
        p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies) if latencies else 0
        throughput = len(queries) / total_time
        
        results_summary[workers] = {
            "avg_latency": avg_latency,
            "p95_latency": p95_latency,
            "throughput_rps": throughput,
            "errors": errors,
            "total_time": total_time
        }
        
        print(f"Results for {workers} workers:")
        print(f"  Avg Latency: {avg_latency:.4f}s")
        print(f"  P95 Latency: {p95_latency:.4f}s")
        print(f"  Throughput: {throughput:.2f} queries/sec")
        print(f"  Errors: {errors}")

    return results_summary

if __name__ == "__main__":
    # A mix of queries to simulate real usage
    test_queries = [
        "machine learning", "climate change", "cancer research", 
        "quantum computing", "artificial intelligence", "deep learning",
        "renewable energy", "genetics", "neuroscience", "nanotechnology",
        "blockchain", "cybersecurity", "data science", "internet of things",
        "cloud computing", "robotics", "augmented reality", "virtual reality",
        "5g networks", "biotechnology"
    ]
    
    # Double the list to have enough for larger concurrency
    test_queries = test_queries * 2 
    
    result = benchmark_search_concurrency(test_queries)
    print("\nBenchmark Complete.")
