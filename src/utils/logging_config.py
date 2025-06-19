"""
Centralized Logging Configuration for Yuga Planner

This module provides a unified logging configuration that:
1. Respects the YUGA_DEBUG environment variable for debug logging
2. Uses consistent formatting across the entire codebase
3. Eliminates the need for individual logging.basicConfig() calls

Usage:
    from utils.logging_config import setup_logging, get_logger

    # Initialize logging (typically done once per module)
    setup_logging()
    logger = get_logger(__name__)

    # Use logging methods
    logger.debug("Debug message - only shown when YUGA_DEBUG=true")
    logger.info("Info message - always shown")
    logger.warning("Warning message")
    logger.error("Error message")

Environment Variables:
    YUGA_DEBUG: Set to "true" to enable debug logging

Migration from old logging:
    Replace:
        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

    With:
        from utils.logging_config import setup_logging, get_logger
        setup_logging()
        logger = get_logger(__name__)
"""

import logging
import os
from typing import Optional


def setup_logging(level: Optional[str] = None) -> None:
    """
    Set up centralized logging configuration for the application.

    Args:
        level: Override the logging level. If None, uses YUGA_DEBUG environment variable.
    """
    # Determine logging level
    if level is not None:
        log_level = getattr(logging, level.upper(), logging.INFO)

    else:
        debug_enabled = os.getenv("YUGA_DEBUG", "false").lower() == "true"
        log_level = logging.DEBUG if debug_enabled else logging.INFO

    # Configure logging
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Log the configuration
    logger = logging.getLogger(__name__)
    logger.debug("Debug logging enabled via YUGA_DEBUG environment variable")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.

    Args:
        name: Name for the logger, typically __name__

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def is_debug_enabled() -> bool:
    """Check if debug logging is enabled via environment variable."""
    return os.getenv("YUGA_DEBUG", "false").lower() == "true"
