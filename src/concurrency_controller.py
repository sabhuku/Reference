import threading
import time
from collections import deque
import statistics
import logging

class CircuitBreaker:
    """Fail-fast mechanism for repeated failures."""
    def __init__(self, failure_threshold=5, recovery_timeout=30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.Lock()

    def record_failure(self):
        with self._lock:
            self.failures += 1
            self.last_failure_time = time.time()
            if self.failures >= self.failure_threshold:
                self.state = "OPEN"
                logging.warning("Circuit Breaker Tripped: OPEN")

    def record_success(self):
        with self._lock:
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failures = 0
                logging.info("Circuit Breaker Recovered: CLOSED")
            elif self.state == "CLOSED":
                self.failures = 0

    def allow_request(self):
        with self._lock:
            if self.state == "CLOSED":
                return True
            if self.state == "OPEN":
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = "HALF_OPEN"
                    return True
                return False
            return True # HALF_OPEN allows 1 request (handled by caller logic usually, simplified here)

class PubMedConcurrencyController:
    """Dynamic concurrency controller using Bounded Hysteresis Step-Control."""
    def __init__(self):
        # Configuration
        self.MIN_CAPACITY = 4
        self.MAX_CAPACITY = 8
        self.WINDOW_SECONDS = 60
        self.COOLDOWN_SECONDS = 30
        
        # State
        self.current_capacity = 8
        self.last_adjustment_time = 0
        self._lock = threading.Lock()
        
        # Metrics: List of (timestamp, latency_or_error)
        self.history = deque()
        
    def record_outcome(self, latency=None, is_429=False):
        """Thread-safe metric recording"""
        now = time.time()
        with self._lock:
            if is_429:
                self.history.append((now, 'error'))
            else:
                self.history.append((now, latency))
            
            # Lazy cleanup
            self._prune_history(now)
            
            # Check for adjustment
            self._evaluate_health(now)

    def get_capacity(self):
        return self.current_capacity

    def _prune_history(self, now):
        while self.history and (now - self.history[0][0] > self.WINDOW_SECONDS):
            self.history.popleft()

    def _evaluate_health(self, now):
        # 1. Hysteresis Check
        if now - self.last_adjustment_time < self.COOLDOWN_SECONDS:
            return

        # 2. Calculate Metrics
        total_events = len(self.history)
        if total_events < 10: # Minimum sample size
            return
            
        errors = sum(1 for _, v in self.history if v == 'error')
        latencies = [v for _, v in self.history if v != 'error']
        
        error_rate = errors / total_events
        p95_latency = 0
        if latencies:
             latencies.sort()
             idx = int(len(latencies) * 0.95)
             p95_latency = latencies[idx]

        # 3. Decision Logic
        new_capacity = self.current_capacity
        
        # DECREASE CONDITIONS
        if error_rate > 0.02:
            logging.info(f"Controller: High Error Rate ({error_rate:.1%}). Decreasing.")
            new_capacity -= 1
        elif p95_latency > 4.5:
            logging.info(f"Controller: High Latency ({p95_latency:.2f}s). Decreasing.")
            new_capacity -= 1
            
        # INCREASE CONDITIONS
        elif error_rate < 0.005 and p95_latency < 3.0:
            logging.info(f"Controller: System healthy (Err={error_rate:.1%}, P95={p95_latency:.2f}s). Increasing.")
            new_capacity += 1
            
        # 4. Apply Bounds & Commit
        new_capacity = max(self.MIN_CAPACITY, min(self.MAX_CAPACITY, new_capacity))
        
        if new_capacity != self.current_capacity:
            self.current_capacity = new_capacity
            self.last_adjustment_time = now
            logging.info(f"Controller: Capacity adjusted to {self.current_capacity}")
