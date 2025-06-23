"""
Test Utilities for Yuga Planner Tests

This module provides standardized logging and common functionality for all test files.
It ensures consistent logging patterns and reduces boilerplate across the test suite.

Usage:
    from tests.test_utils import TestLogger, test_config

    # At the top of any test file
    logger = TestLogger(__name__)

    # In test functions
    def test_something():
        logger.start_test("Testing important functionality")
        logger.info("✅ Test step passed")
        logger.debug("Debug details...")
        logger.pass_test("Important functionality works correctly")

Environment Variables:
    YUGA_DEBUG: Set to "true" to enable detailed debug logging in tests
    PYTEST_CURRENT_TEST: Automatically set by pytest with current test info
"""

import os
import sys
from typing import Optional, Dict, Any

# Add src to path to import our modules (for tests that use this utility)
if "src" not in [p.split("/")[-1] for p in sys.path]:
    sys.path.insert(0, "src")

from utils.logging_config import setup_logging, get_logger, is_debug_enabled

# Initialize logging early for all tests
setup_logging()


class TestLogger:
    """
    Standardized logger for test files with test-specific formatting and methods.

    Provides consistent logging patterns across all test files with special
    methods for test lifecycle events.
    """

    def __init__(self, name: str):
        """
        Initialize test logger for a specific test module.

        Args:
            name: Usually __name__ from the test file
        """
        self.logger = get_logger(name)
        self.current_test = None

        # Log test module initialization
        module_name = name.split(".")[-1] if "." in name else name
        self.logger.debug(f"🧪 Initialized test logger for {module_name}")

    def start_test(self, test_description: str) -> None:
        """Mark the start of a test with description."""
        self.current_test = test_description
        self.logger.info(f"🧪 {test_description}")

    def pass_test(self, message: str = None) -> None:
        """Mark a test as passed with optional message."""
        msg = message or self.current_test or "Test"
        self.logger.info(f"✅ SUCCESS: {msg}")

    def fail_test(self, message: str, exception: Exception = None) -> None:
        """Mark a test as failed with message and optional exception."""
        if exception:
            self.logger.error(f"❌ FAILED: {message} - {exception}")
        else:
            self.logger.error(f"❌ FAILED: {message}")

    def skip_test(self, reason: str) -> None:
        """Mark a test as skipped with reason."""
        self.logger.warning(f"⏭️ SKIPPED: {reason}")

    def info(self, message: str) -> None:
        """Log an info message."""
        self.logger.info(message)

    def debug(self, message: str) -> None:
        """Log a debug message (only shown when YUGA_DEBUG=true)."""
        self.logger.debug(message)

    def warning(self, message: str) -> None:
        """Log a warning message."""
        self.logger.warning(message)

    def error(self, message: str) -> None:
        """Log an error message."""
        self.logger.error(message)

    def section(self, title: str) -> None:
        """Log a section header for organizing test output."""
        separator = "=" * 60
        self.logger.info(separator)
        self.logger.info(f"📋 {title}")
        self.logger.info(separator)

    def subsection(self, title: str) -> None:
        """Log a subsection header."""
        self.logger.info(f"\n📌 {title}")
        self.logger.info("-" * 40)


class TestResults:
    """
    Track and report test results consistently across test files.

    Provides methods to track pass/fail status and generate summary reports.
    """

    def __init__(self, logger: TestLogger):
        self.logger = logger
        self.results: Dict[str, bool] = {}
        self.details: Dict[str, str] = {}

    def add_result(self, test_name: str, passed: bool, details: str = None) -> None:
        """Add a test result."""
        self.results[test_name] = passed
        if details:
            self.details[test_name] = details

        status = "✅ PASS" if passed else "❌ FAIL"
        self.logger.info(f"  {test_name.replace('_', ' ').title()}: {status}")
        if details and not passed:
            self.logger.debug(f"    Details: {details}")

    def run_test(self, test_name: str, test_func, *args, **kwargs) -> bool:
        """
        Run a test function and automatically track results.

        Args:
            test_name: Name for result tracking
            test_func: Test function to execute
            *args, **kwargs: Arguments for test function

        Returns:
            bool: True if test passed, False if failed
        """
        try:
            test_func(*args, **kwargs)
            self.add_result(test_name, True)
            return True
        except Exception as e:
            self.add_result(test_name, False, str(e))
            return False

    def summary(self) -> bool:
        """
        Generate and log test summary.

        Returns:
            bool: True if all tests passed, False otherwise
        """
        total_tests = len(self.results)
        passed_tests = sum(1 for passed in self.results.values() if passed)

        self.logger.section("Test Results Summary")
        self.logger.info(f"📊 Tests Run: {total_tests}")
        self.logger.info(f"✅ Passed: {passed_tests}")
        self.logger.info(f"❌ Failed: {total_tests - passed_tests}")

        # Log individual results
        for test_name, passed in self.results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            self.logger.info(f"  {test_name.replace('_', ' ').title()}: {status}")

            # Show failure details if available
            if not passed and test_name in self.details:
                self.logger.debug(f"    Error: {self.details[test_name]}")

        all_passed = all(self.results.values())
        if all_passed:
            self.logger.info("🎉 ALL TESTS PASSED!")
        else:
            self.logger.error("❌ SOME TESTS FAILED!")

        return all_passed


# Global test configuration
test_config = {
    "debug_enabled": is_debug_enabled(),
    "pytest_running": "PYTEST_CURRENT_TEST" in os.environ,
    "log_level": "DEBUG" if is_debug_enabled() else "INFO",
}

# Convenience functions for quick access
def get_test_logger(name: str) -> TestLogger:
    """Get a standardized test logger."""
    return TestLogger(name)


def create_test_results(logger: TestLogger) -> TestResults:
    """Create a test results tracker."""
    return TestResults(logger)


def log_test_environment() -> None:
    """Log information about the test environment."""
    logger = get_test_logger(__name__)
    logger.debug(f"🔧 Test environment - Debug: {test_config['debug_enabled']}")
    logger.debug(f"🔧 Running under pytest: {test_config['pytest_running']}")
    logger.debug(f"🔧 Log level: {test_config['log_level']}")
