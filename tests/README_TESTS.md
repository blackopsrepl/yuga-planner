# Yuga Planner Test Framework Instructions

## Overview
This document provides instructions for writing, running, and maintaining tests in the Yuga Planner project using our standardized test framework.

## Quick Start

### Running Tests

#### Standard Testing (recommended for CI/CD)
```bash
pytest tests/test_*.py -v
```

#### Debug Mode (detailed output for troubleshooting)
```bash
YUGA_DEBUG=true pytest tests/test_*.py -v -s
```

#### Direct Execution (individual test files)
```bash
python tests/test_specific_file.py
YUGA_DEBUG=true python tests/test_specific_file.py  # with debug output
```

## Writing Tests

### 1. Basic Test Structure

Every test file should follow this pattern:

```python
import sys
from tests.test_utils import get_test_logger, create_test_results

# Initialize logging
logger = get_test_logger(__name__)

def test_your_feature():
    """Test function that works with both pytest and direct execution."""
    logger.start_test("Description of what you're testing")

    try:
        # Your test logic here
        result = your_function_to_test()

        # Use assertions for validation
        assert result is not None, "Result should not be None"
        assert result.status == "success", f"Expected success, got {result.status}"

        logger.pass_test("Feature works correctly")

    except Exception as e:
        logger.fail_test(f"Test failed: {str(e)}")
        raise

# Direct execution support
if __name__ == "__main__":
    results = create_test_results(logger)
    results.run_test('test_your_feature', test_your_feature)
    all_passed = results.summary()
    sys.exit(0 if all_passed else 1)
```

### 2. Test Utilities Reference

#### TestLogger Methods

```python
from tests.test_utils import get_test_logger
logger = get_test_logger(__name__)

# Test lifecycle
logger.start_test("Test description")      # Mark test beginning
logger.pass_test("Success message")        # Log successful completion
logger.fail_test("Error message")          # Log test failure

# Organization
logger.section("Section Title")            # Create visual separators

# Standard logging levels
logger.debug("Detailed debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error message")
```

#### TestResults Methods

```python
from tests.test_utils import create_test_results

results = create_test_results(logger)

# Run tests with automatic error handling
results.run_test('test_name', test_function)

# Generate summary and get overall result
all_passed = results.summary()  # Returns True if all tests passed

# Use for exit codes
sys.exit(0 if all_passed else 1)
```

### 3. Async Test Pattern

For async tests, use this pattern:

```python
import asyncio
import pytest

@pytest.mark.asyncio
async def test_async_feature():
    """Async test that works with pytest."""
    logger.start_test("Testing async functionality")

    try:
        result = await your_async_function()
        assert result.is_valid(), "Async result should be valid"
        logger.pass_test("Async functionality works")
    except Exception as e:
        logger.fail_test(f"Async test failed: {str(e)}")
        raise

# For direct execution of async tests
async def run_async_tests():
    """Helper for running async tests directly."""
    logger.section("Async Tests")
    await test_async_feature()

if __name__ == "__main__":
    results = create_test_results(logger)
    # Use asyncio.run for async test execution
    results.run_test('async_tests', lambda: asyncio.run(run_async_tests()))
    all_passed = results.summary()
    sys.exit(0 if all_passed else 1)
```

### 4. Complex Test Files

For files with multiple test functions:

```python
def test_feature_one():
    logger.start_test("Testing feature one")
    # ... test logic ...
    logger.pass_test("Feature one works")

def test_feature_two():
    logger.start_test("Testing feature two")
    # ... test logic ...
    logger.pass_test("Feature two works")

def test_integration():
    logger.start_test("Testing integration")
    # ... test logic ...
    logger.pass_test("Integration works")

if __name__ == "__main__":
    results = create_test_results(logger)

    # Run all tests
    results.run_test('feature_one', test_feature_one)
    results.run_test('feature_two', test_feature_two)
    results.run_test('integration', test_integration)

    # Generate summary
    all_passed = results.summary()
    sys.exit(0 if all_passed else 1)
```

## Environment Control

### Debug Output Control

The framework respects the `YUGA_DEBUG` environment variable:

- **`YUGA_DEBUG=false` or unset**: Minimal output suitable for CI/CD
- **`YUGA_DEBUG=true`**: Detailed debug output for troubleshooting

### Usage Examples

```bash
# Quiet mode (default)
pytest tests/test_factory.py -v

# Debug mode
YUGA_DEBUG=true pytest tests/test_factory.py -v -s

# Direct execution with debug
YUGA_DEBUG=true python tests/test_constraints.py
```

## Best Practices

### 1. Test Organization

- Use descriptive test function names: `test_calendar_event_creation_with_constraints`
- Group related tests in the same file
- Use `logger.section()` to separate different test groups within a file

### 2. Error Messages

- Always provide clear assertion messages:
  ```python
  assert result.count == 5, f"Expected 5 items, got {result.count}"
  ```

### 3. Test Lifecycle

- Always use `logger.start_test()` at the beginning of each test
- Use `logger.pass_test()` or `logger.fail_test()` to mark completion
- Let exceptions propagate for pytest compatibility

### 4. Output Structure

- Use sections to organize output:
  ```python
  logger.section("Calendar Operations Tests")
  # ... run calendar tests ...

  logger.section("Task Management Tests")
  # ... run task tests ...
  ```

## Integration with Existing Code

### Pytest Compatibility

The framework is fully compatible with existing pytest features:

- Test discovery works without changes
- Fixtures continue to work normally
- Async tests work with `@pytest.mark.asyncio`
- All pytest command-line options are supported

### Logging Integration

- Integrates with project's `utils.logging_config`
- Respects existing logging configuration
- No interference with application logging

## Troubleshooting

### Common Issues

1. **Tests run but no output**: Ensure you're using `-s` flag with pytest in debug mode
2. **Import errors**: Make sure `tests/test_utils.py` is accessible
3. **Async tests failing**: Use `@pytest.mark.asyncio` for pytest, `asyncio.run()` for direct execution

### Debug Mode Benefits

When `YUGA_DEBUG=true`:
- Detailed function entry/exit logging
- Variable state information
- Extended error messages
- Test timing information

## Example Test Files

Refer to these existing test files for patterns:

- `tests/test_calendar_operations.py` - Basic synchronous tests
- `tests/test_task_composer_agent.py` - Async test patterns
- `tests/test_constraints.py` - Large pytest-based test suite
- `tests/test_factory.py` - Complex test file with multiple test types

## Summary

This test framework provides:
- **Consistency** across all test files
- **Flexibility** for different execution modes
- **Professional** output suitable for development and CI/CD
- **Maintainability** through centralized utilities
- **Compatibility** with existing pytest workflows

Follow these patterns for all new tests to maintain consistency and leverage the full power of the test framework.
