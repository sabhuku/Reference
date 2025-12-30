"""API utilities and error handling for reference management."""
import requests
from typing import Optional, Dict, Any
from functools import wraps
import logging

def api_error_handler(func):
    """
    Decorator for handling API request errors.
    
    Args:
        func: The function to wrap
        
    Returns:
        Wrapped function with error handling
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.ConnectionError:
            logging.error("Could not connect to API. Please check your internet connection.")
        except requests.Timeout:
            logging.error("Request to API timed out. Please try again.")
        except requests.RequestException as e:
            logging.error(f"API request failed: {str(e)}")
        except ValueError as e:
            logging.error(f"Error processing API response: {str(e)}")
        except Exception as e:
            logging.error(f"Unexpected error: {str(e)}")
        return None
    return wrapper

def safe_request(url: str, params: Dict[str, Any], timeout: int = 10) -> Optional[Dict]:
    """
    Make a safe HTTP GET request with error handling.
    
    Args:
        url: The URL to request
        params: Query parameters
        timeout: Request timeout in seconds
        
    Returns:
        Optional[Dict]: JSON response if successful, None otherwise
    """
    try:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.ConnectionError:
        logging.error(f"Connection error while accessing {url}")
    except requests.Timeout:
        logging.error(f"Request timeout while accessing {url}")
    except requests.RequestException as e:
        logging.error(f"Request failed for {url}: {str(e)}")
    except ValueError as e:
        logging.error(f"Invalid JSON response from {url}: {str(e)}")
    return None