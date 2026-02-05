
import time
import requests
import statistics
from src.api import CrossRefAPI, GoogleBooksAPI, PubMedAPI
from src.config import Config

def measure_api_latency(api_func, query, iterations=5):
    latencies = []
    successes = 0
    
    for _ in range(iterations):
        start = time.time()
        try:
            results = api_func(query)
            duration = time.time() - start
            latencies.append(duration)
            if results:
                successes += 1
        except Exception as e:
            print(f"Error: {e}")
            pass
            
    return latencies, successes

def benchmark_apis():
    config = Config()
    crossref = CrossRefAPI(config.CROSSREF_MAILTO)
    pubmed = PubMedAPI()
    google_books = GoogleBooksAPI(config.GOOGLE_BOOKS_API_KEY)
    
    query = "machine learning"
    iterations = 5
    
    print(f"Benchmarking APIs with query: '{query}' ({iterations} iterations each)...")
    
    # CrossRef
    print("\nTesting CrossRef...")
    cr_latencies, cr_success = measure_api_latency(lambda q: crossref.search(q, rows=5), query, iterations)
    
    # PubMed
    print("Testing PubMed...")
    pm_latencies, pm_success = measure_api_latency(lambda q: pubmed.search(q, max_results=5), query, iterations)
    
    # Google Books
    print("Testing Google Books...")
    gb_latencies, gb_success = measure_api_latency(lambda q: google_books.search(q, max_results=5), query, iterations)
    
    results = {
        "CrossRef": {"latencies": cr_latencies, "success_rate": cr_success/iterations},
        "PubMed": {"latencies": pm_latencies, "success_rate": pm_success/iterations},
        "GoogleBooks": {"latencies": gb_latencies, "success_rate": gb_success/iterations}
    }
    
    for name, data in results.items():
        lats = data['latencies']
        if lats:
            avg = statistics.mean(lats)
            stdev = statistics.stdev(lats) if len(lats) > 1 else 0
            print(f"\n{name}:")
            print(f"  Avg Latency: {avg:.4f}s")
            print(f"  Std Dev: {stdev:.4f}s")
            print(f"  Success My Rate: {data['success_rate']*100}%")
        else:
             print(f"\n{name}: No successful requests.")

if __name__ == "__main__":
    benchmark_apis()
