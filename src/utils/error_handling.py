"""Error handling utilities."""
import logging
from functools import wraps
from typing import Callable, Any

def api_error_handler(func: Callable) -> Callable:
    """Decorator for handling API-related errors."""
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error(f"API error in {func.__name__}: {str(e)}")
            return None
    return wrapper

def file_operation_handler(func: Callable) -> Callable:
    """Decorator for handling file operation errors."""
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error(f"File operation error in {func.__name__}: {str(e)}")
            return None
    return wrapper

def user_input_handler(func: Callable) -> Callable:
    """Decorator for handling user input errors."""
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
            return None
        except Exception as e:
            logging.error(f"Input error in {func.__name__}: {str(e)}")
            return None
    return wrapper