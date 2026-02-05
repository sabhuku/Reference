import time
import random
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.concurrency_controller import PubMedConcurrencyController

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def simulate_pubmed_request(controller):
    """
    Simulates a single PubMed request.
    Behavior depends on global 'SIMULATION_STATE'.
    """
    state = SIMULATION_STATE
    
    # 1. Simulate Latency
    base_latency = 2.5
    if state['high_latency']:
        base_latency = 5.0
    
    latency = random.normalvariate(base_latency, 0.5)
    latency = max(0.1, latency)
    
    # 2. Simulate Network Delay (Sleep)
    # In a real test we would sleep, but for simulation speed up we can just "pretend" time passed 
    # OR strictly sleep. Let's sleep to test the real time-based controller.
    # Speed up factor: 1s real = 1s simulated (real-time test)
    time.sleep(latency * 0.1) # Accelerated 10x for test speed
    
    # 3. Simulate Outcome
    is_429 = False
    if state['error_rate'] > 0:
        if random.random() < state['error_rate']:
            is_429 = True
    
    # Report to controller (scale latency back up if we accelerated time)
    controller.record_outcome(latency=latency, is_429=is_429)

# Global simulation state
SIMULATION_STATE = {
    'high_latency': False,
    'error_rate': 0.0
}

def run_simulation():
    controller = PubMedConcurrencyController()
    # Speed up controller for test
    controller.WINDOW_SECONDS = 6  # 6s window (simulates 60s)
    controller.COOLDOWN_SECONDS = 3 # 3s cooldown (simulates 30s)
    
    print("Time,Capacity,P95_Est,Error_Est")
    
    start_time = time.time()
    
    # Phase 1: Normal Operation (20s) - Should climb to 8
    print("--- Phase 1: Normal Load ---")
    end_phase_1 = start_time + 10
    while time.time() < end_phase_1:
         simulate_pubmed_request(controller)
         time.sleep(0.05) # fast arrival
         print(f"{time.time()-start_time:.1f},{controller.get_capacity()},Normal")

    # Phase 2: High Latency (10s) - Should drop
    print("--- Phase 2: High Latency (P95 > 4.5s) ---")
    SIMULATION_STATE['high_latency'] = True
    end_phase_2 = end_phase_1 + 10
    while time.time() < end_phase_2:
         simulate_pubmed_request(controller)
         time.sleep(0.05)
         print(f"{time.time()-start_time:.1f},{controller.get_capacity()},HighLat")

    # Phase 3: Recovery (10s) - Should climb
    print("--- Phase 3: Recovery ---")
    SIMULATION_STATE['high_latency'] = False
    end_phase_3 = end_phase_2 + 10
    while time.time() < end_phase_3:
         simulate_pubmed_request(controller)
         time.sleep(0.05)
         print(f"{time.time()-start_time:.1f},{controller.get_capacity()},Recovery")

    # Phase 4: High Errors (10s) - Should drop
    print("--- Phase 4: High Errors (Rate > 2%) ---")
    SIMULATION_STATE['error_rate'] = 0.10 # 10% errors
    end_phase_4 = end_phase_3 + 10
    while time.time() < end_phase_4:
         simulate_pubmed_request(controller)
         time.sleep(0.05)
         print(f"{time.time()-start_time:.1f},{controller.get_capacity()},HighErr")

if __name__ == "__main__":
    run_simulation()
