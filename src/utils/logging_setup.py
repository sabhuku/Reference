"""Logging configuration."""
import logging
from datetime import datetime
import os
from pathlib import Path

def setup_logging(log_dir: str = "logs", level: int = logging.INFO) -> None:
    """Set up logging configuration."""
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
    handlers = [
        logging.FileHandler(log_file),
        logging.StreamHandler()  # Console output
    ]
    
    # Configure logging
    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt=date_format,
        handlers=handlers
    )
    
    logging.info("Logging initialized")
    logging.info(f"Log file: {log_file}")

def log_operation(operation: str, details: str, level: int = logging.INFO) -> None:
    """Log an operation with details."""
    logging.log(level, f"{operation}: {details}")

def log_api_call(api: str, method: str, params: dict) -> None:
    """Log an API call."""
    logging.info(f"API Call - {api}.{method}({params})")