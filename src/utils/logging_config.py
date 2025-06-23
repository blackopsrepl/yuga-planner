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

import os, sys, logging, threading, time

from typing import Optional

from collections import deque


class LogCapture:
    """Capture logs for real-time streaming to UI"""

    def __init__(self, max_lines: int = 1000):
        self.max_lines = max_lines
        self.log_buffer = deque(maxlen=max_lines)
        self.session_buffer = deque(maxlen=max_lines)  # Current session logs
        self.lock = threading.Lock()
        self.session_start_time = None

    def add_log(self, record: logging.LogRecord):
        """Add a log record to the UI streaming buffer (filtered for essential logs only)"""
        # This only affects UI streaming - console logs are handled separately
        logger_name = record.name
        message = record.getMessage()

        # Skip all UI, gradio, httpx, and other system logs for UI streaming
        skip_loggers = [
            "gradio",
            "httpx",
            "uvicorn",
            "fastapi",
            "urllib3",
            "ui.pages.chat",
            "ui.",
            "asyncio",
            "websockets",
            "handlers.tool_call_handler",
            "services.mcp_client",
        ]

        # Skip if it's a system logger
        if any(skip in logger_name for skip in skip_loggers):
            return

        # Only include essential task splitting and constraint solver logs for UI
        essential_patterns = [
            "=== Step 1: Task Breakdown ===",
            "=== Step 2: Time Estimation ===",
            "=== Step 3: Skill Matching ===",
            "Processing",
            "tasks for time estimation",
            "Completed time estimation",
            "Completed skill matching",
            "Generated",
            "tasks with skills",
            "Starting solve process",
            "Preparing schedule for solving",
            "Starting schedule solver",
            "solving",
            "constraint",
            "optimization",
        ]

        # Check if this log message contains essential information
        is_essential = any(
            pattern.lower() in message.lower() for pattern in essential_patterns
        )

        # Only include essential logs from factory and handler modules for UI
        allowed_modules = ["factory.", "handlers.mcp_backend", "services.schedule"]
        module_allowed = any(
            logger_name.startswith(module) for module in allowed_modules
        )

        if not (module_allowed and is_essential):
            return

        # Format for clean streaming display in UI
        timestamp = time.strftime("%H:%M:%S", time.localtime(record.created))

        # Clean up the message for better display
        match message:
            case msg if "===" in msg:
                # Task breakdown steps
                formatted_log = f"⏳ {msg.replace('===', '').strip()}"

            case msg if "Processing" in msg and "time estimation" in msg:
                formatted_log = f"⏱️ {msg}"

            case msg if "Completed" in msg:
                formatted_log = f"✅ {msg}"

            case msg if "Generated" in msg and "tasks" in msg:
                formatted_log = f"🎯 {msg}"

            case msg if "Starting solve process" in msg or "Starting schedule solver" in msg:
                formatted_log = f"⚡ {msg}"

            case msg if "Preparing schedule" in msg:
                formatted_log = f"📋 {msg}"

            case _:
                formatted_log = f"🔧 {message}"

        with self.lock:
            self.log_buffer.append(formatted_log)

            # Add to session buffer if session is active
            if self.session_start_time and record.created >= self.session_start_time:
                self.session_buffer.append(formatted_log)

    def start_session(self):
        """Start capturing logs for current session"""
        with self.lock:
            self.session_start_time = time.time()
            self.session_buffer.clear()

    def get_session_logs(self) -> list:
        """Get all logs from current session"""
        with self.lock:
            return list(self.session_buffer)

    def get_recent_logs(self, count: int = 50) -> list:
        """Get recent logs"""
        with self.lock:
            return list(self.log_buffer)[-count:]


class StreamingLogHandler(logging.Handler):
    """Custom log handler that captures logs for streaming"""

    def __init__(self, log_capture: LogCapture):
        super().__init__()
        self.log_capture = log_capture

    def emit(self, record):
        try:
            self.log_capture.add_log(record)
        except Exception:
            self.handleError(record)


# Global log capture instance
_log_capture = LogCapture()
_streaming_handler = None


def setup_logging(level: Optional[str] = None) -> None:
    """
    Set up centralized logging configuration for the application.

    Args:
        level: Override the logging level. If None, uses YUGA_DEBUG environment variable.
    """
    global _streaming_handler

    # Determine logging level
    if level is not None:
        log_level = getattr(logging, level.upper(), logging.INFO)
    else:
        debug_enabled = os.getenv("YUGA_DEBUG", "false").lower() == "true"
        log_level = logging.DEBUG if debug_enabled else logging.INFO

    # Get root logger
    root_logger = logging.getLogger()

    # Only configure if not already configured
    if not root_logger.handlers or _streaming_handler is None:
        # Clear existing handlers to avoid duplicates
        root_logger.handlers.clear()

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Console handler for terminal output (shows ALL logs)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)

        # Streaming handler for UI capture (filtered to essential logs only)
        _streaming_handler = StreamingLogHandler(_log_capture)
        _streaming_handler.setLevel(
            logging.DEBUG
        )  # Capture all levels, but filter in handler

        # Configure root logger
        root_logger.setLevel(logging.DEBUG)

        # Add both handlers
        root_logger.addHandler(console_handler)
        root_logger.addHandler(_streaming_handler)

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


def get_log_capture() -> LogCapture:
    """Get the global log capture instance for UI streaming"""
    return _log_capture


def start_session_logging():
    """Start capturing logs for the current chat session"""
    _log_capture.start_session()


def get_session_logs() -> list:
    """Get all logs from the current session for streaming to UI"""
    return _log_capture.get_session_logs()
