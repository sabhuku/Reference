"""Rate limiting utilities for API requests."""
import time
from functools import wraps
from typing import Callable, TypeVar, Any, cast

F = TypeVar('F', bound=Callable[..., Any])

class RateLimiter:
    """Simple rate limiter for API requests that works both as a decorator and context manager."""
    
    def __init__(self, max_calls: int, period: float):
        """
        Initialize rate limiter.
        
        Args:
            max_calls: Maximum number of calls allowed in the period
            period: Time period in seconds
        """
        self.max_calls = max_calls
        self.period = period
        self.calls: list[float] = []
    
    def __enter__(self):
        """Context manager entry - wait if needed before proceeding."""
        self._wait_if_needed()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - record the call time."""
        self.calls.append(time.time())
        self._cleanup()
        
    def __call__(self, func: F) -> F:
        """Decorator to rate limit function calls."""
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with self:
                return func(*args, **kwargs)
        
        return cast(F, wrapper)
    
    def _wait_if_needed(self) -> None:
        """Wait if rate limit would be exceeded."""
        now = time.time()
        self._cleanup()
        
        if len(self.calls) >= self.max_calls:
            sleep_time = self.calls[0] + self.period - now
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    def _cleanup(self) -> None:
        """Remove old timestamps from the call history."""
        now = time.time()
        self.calls = [t for t in self.calls if now - t < self.period]

# Default rate limiters for common APIs
CROSSREF_RATE_LIMITER = RateLimiter(max_calls=50, period=1)  # 50 requests per second
GOOGLE_BOOKS_RATE_LIMITER = RateLimiter(max_calls=100, period=100)  # 100 requests per 100 seconds
