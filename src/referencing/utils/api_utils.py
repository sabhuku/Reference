"""API utilities with retry and error handling."""
import json
import logging
import time
from functools import wraps
from typing import Any, Callable, TypeVar, Optional, Dict, Union, List, Tuple, cast
import requests
from requests import Response
from requests.exceptions import RequestException

from referencing.config_loader import Config
from .rate_limiter import CROSSREF_RATE_LIMITER, GOOGLE_BOOKS_RATE_LIMITER

logger = logging.getLogger(__name__)

F = TypeVar('F', bound=Callable[..., Any])

def retry(
    max_retries: int = 3,
    backoff_factor: float = 0.5,
    status_codes: Optional[List[int]] = None,
) -> Callable[[F], F]:
    """
    Retry decorator with exponential backoff.
    
    Args:
        max_retries: Maximum number of retries
        backoff_factor: Backoff multiplier (e.g., 0.5 = 0.5, 1, 2, 4, ... seconds)
        status_codes: HTTP status codes to retry on. Defaults to [429, 500, 502, 503, 504]
    """
    if status_codes is None:
        status_codes = [429, 500, 502, 503, 504]
    
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            retries = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except RequestException as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(
                            f"Max retries ({max_retries}) exceeded for {func.__name__}: {str(e)}"
                        )
                        raise
                    
                    wait_time = backoff_factor * (2 ** (retries - 1))
                    logger.warning(
                        f"Retry {retries}/{max_retries} for {func.__name__} "
                        f"after error: {str(e)}. Waiting {wait_time:.2f} seconds..."
                    )
                    time.sleep(wait_time)
                except Exception as e:
                    logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
                    raise
        
        return cast(F, wrapper)
    return decorator

class APIError(Exception):
    """Base exception for API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, response_text: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.status_code:
            return f"{self.message} (Status: {self.status_code})"
        return self.message

def handle_api_response(response: Response, api_name: str = "API") -> Dict[str, Any]:
    """
    Handle API response and raise appropriate exceptions.
    
    Args:
        response: The response object from requests
        api_name: Name of the API for error messages
        
    Returns:
        Parsed JSON response
        
    Raises:
        APIError: If the response indicates an error
    """
    try:
        response.raise_for_status()
        return response.json()
    except requests.exceptions.JSONDecodeError:
        error_msg = f"{api_name} returned invalid JSON"
        logger.error(f"{error_msg}: {response.text[:200]}...")
        raise APIError(error_msg, response.status_code, response.text)
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response else None
        error_msg = f"{api_name} request failed"
        logger.error(f"{error_msg} (Status: {status_code}): {str(e)}")
        raise APIError(error_msg, status_code, str(e)) from e

@retry()
def safe_crossref_request(url: str, params: Optional[Dict[str, Any]] = None):
    """
    Make a safe request to the Crossref API with rate limiting and retries.
    
    Args:
        url: The URL to request
        params: Query parameters
        
    Returns:
        Parsed JSON response
    """
    if params is None:
        params = {}
    
    # Add mailto parameter if not present
    if 'mailto' not in params and Config.CROSSREF_MAILTO:
        params['mailto'] = Config.CROSSREF_MAILTO
    
    logger.info(f"Making request to Crossref API: {url}")
    logger.debug(f"Request params: {params}")
    
    try:
        # Apply rate limiting using the decorator pattern
        @CROSSREF_RATE_LIMITER
        def make_request():
            start_time = time.time()
            response = requests.get(url, params=params, timeout=30)
            elapsed = time.time() - start_time
            
            logger.info(f"Crossref API request completed in {elapsed:.2f}s - Status: {response.status_code}")
            
            # Log response details for debugging
            if response.status_code != 200:
                logger.error(f"Error response from Crossref API: {response.status_code} - {response.text[:500]}")
            else:
                logger.debug(f"Response headers: {dict(response.headers)}")
                logger.debug(f"Response content (first 500 chars): {response.text[:500]}")
            
            # Parse and return the response
            result = handle_api_response(response, "Crossref API")
            logger.debug("Successfully parsed API response")
            return result
            
        return make_request()
            
    except Exception as e:
        logger.error(f"Error in safe_crossref_request: {str(e)}", exc_info=True)
        raise

@retry()
def safe_google_books_request(url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Make a safe request to the Google Books API with rate limiting and retries.
    
    Args:
        url: The URL to request
        params: Query parameters
        
    Returns:
        Parsed JSON response
    """
    if params is None:
        params = {}
    
    # Add API key if available
    if 'key' not in params and Config.GOOGLE_BOOKS_API_KEY:
        params['key'] = Config.GOOGLE_BOOKS_API_KEY
    
    logger.info(f"Making request to Google Books API: {url}")
    logger.debug(f"Request params: {params}")
    
    try:
        # Apply rate limiting using the decorator pattern
        @GOOGLE_BOOKS_RATE_LIMITER
        def make_request():
            start_time = time.time()
            response = requests.get(url, params=params, timeout=30)
            elapsed = time.time() - start_time
            
            logger.info(f"Google Books API request completed in {elapsed:.2f}s - Status: {response.status_code}")
            
            # Log response details for debugging
            if response.status_code != 200:
                logger.error(f"Error response from Google Books API: {response.status_code} - {response.text[:500]}")
            
            return handle_api_response(response, "Google Books API")
            
        return make_request()
            
    except Exception as e:
        logger.error(f"Error in safe_google_books_request: {str(e)}", exc_info=True)
        raise
