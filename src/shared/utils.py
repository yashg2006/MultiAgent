"""
Shared utility helper functions (e.g., logging setup, retry logic, formatting).
"""

import logging

def setup_logger(name: str) -> logging.Logger:
    """Configure a standard logger instance."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s [%(name)s]: %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
