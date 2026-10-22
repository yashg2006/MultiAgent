"""
Shared utility helpers (logging setup).
"""

import logging
import os

from src.shared.observability import ContextFilter, make_formatter


def setup_logger(name: str) -> logging.Logger:
    """A logger that writes to stderr with request/task ids attached.

    Format comes from LOG_FORMAT ("text" by default, "json" for log
    collectors); level from LOG_LEVEL (default INFO). Idempotent: calling it
    again for the same name returns the same logger without new handlers.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(make_formatter(os.getenv("LOG_FORMAT", "text")))
        handler.addFilter(ContextFilter())
        logger.addHandler(handler)
        logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
        logger.propagate = False
    return logger
