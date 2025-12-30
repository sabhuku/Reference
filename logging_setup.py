import logging
from pathlib import Path
from datetime import datetime

def setup_logging(log_dir: str = "logs") -> None:
    """Setup logging configuration."""
    # Create logs directory if it doesn't exist
    Path(log_dir).mkdir(exist_ok=True)
    
    # Create log filename with timestamp
    log_file = Path(log_dir) / f"referencing_{datetime.now():%Y%m%d_%H%M%S}.log"
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()  # Also print to console
        ]
    )
    
    logging.info("Logging initialized")