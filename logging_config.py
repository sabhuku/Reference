"""Logging configuration for reference management."""
import logging
from datetime import datetime
import os
from pathlib import Path

def setup_logging(log_dir: str = "logs", level: int = logging.INFO) -> None:
    """
    Set up logging configuration.
    
    Args:
        log_dir: Directory to store log files
        level: Logging level
    """
    # Create logs directory
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Create log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_path / f"referencing_{timestamp}.log"
    
    # Configure logging format
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Set up handlers
    file_handler = logging.FileHandler(log_file)
    console_handler = logging.StreamHandler()
    
    # Configure formatters
    formatter = logging.Formatter(log_format, date_format)
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    logging.info("Logging initialized")
    logging.info(f"Log file: {log_file}")

def log_api_call(api_name: str, endpoint: str) -> None:
    """
    Log API call details.
    
    Args:
        api_name: Name of the API
        endpoint: API endpoint called
    """
    logging.info(f"Calling {api_name} API: {endpoint}")

def log_error(error_type: str, details: str) -> None:
    """
    Log error details.
    
    Args:
        error_type: Type of error
        details: Error details
    """
    logging.error(f"{error_type}: {details}")

def log_success(operation: str, details: str) -> None:
    """
    Log successful operations.
    
    Args:
        operation: Type of operation
        details: Operation details
    """
    logging.info(f"Success - {operation}: {details}")