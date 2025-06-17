import logging
import threading
from datetime import datetime
from typing import List


class LogCapture:
    """Helper class to capture logs for streaming to UI"""

    def __init__(self):
        self.logs: List[str] = []
        self.lock = threading.Lock()

    def add_log(self, message: str) -> None:
        """Add a log message with timestamp"""
        with self.lock:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.logs.append(f"[{timestamp}] {message}")

    def get_logs(self) -> str:
        """Get all accumulated logs as a single string"""
        with self.lock:
            return "\n".join(self.logs)

    def clear(self) -> None:
        """Clear all accumulated logs"""
        with self.lock:
            self.logs.clear()


class StreamingLogHandler(logging.Handler):
    """Custom log handler that captures logs for UI streaming"""

    def __init__(self, log_capture: LogCapture):
        super().__init__()
        self.log_capture = log_capture

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self.log_capture.add_log(msg)
        except Exception:
            self.handleError(record)


class LoggingService:
    """Service for managing log streaming and capture for the UI"""

    def __init__(self):
        self.log_capture = LogCapture()
        self._handler_added = False

    def setup_log_streaming(self) -> None:
        """Set up log streaming to capture logs for UI"""
        logger = logging.getLogger()

        # Remove existing handlers to avoid duplicate logs
        for handler in logger.handlers[:]:
            if isinstance(handler, StreamingLogHandler):
                logger.removeHandler(handler)

        # Add our streaming handler
        stream_handler = StreamingLogHandler(self.log_capture)
        stream_handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(levelname)s - %(message)s")
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
        self._handler_added = True

    def get_streaming_logs(self) -> str:
        """Get accumulated logs for streaming to UI"""
        return self.log_capture.get_logs()

    def clear_streaming_logs(self) -> None:
        """Clear accumulated logs"""
        self.log_capture.clear()

    def is_setup(self) -> bool:
        """Check if log streaming is set up"""
        return self._handler_added
