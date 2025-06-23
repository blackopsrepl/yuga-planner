#!/usr/bin/env python3
"""
Test script for tool call assembly logic
"""

import json
import sys
import os

# Add src to path so we can import modules
sys.path.insert(0, "src")

from handlers.tool_call_handler import ToolCallAssembler

# Import standardized test utilities
from tests.test_utils import get_test_logger, create_test_results

# Initialize standardized test logger
logger = get_test_logger(__name__)


def test_tool_call_assembly():
    """Test the tool call assembler with sample streaming data"""

    logger.start_test("Testing Tool Call Assembly Logic")

    assembler = ToolCallAssembler()

    # Simulate streaming deltas like we saw in the logs
    sample_deltas = [
        # Initial tool call with ID
        {
            "tool_calls": [
                {
                    "index": 0,
                    "id": "chatcmpl-tool-ca3c56dcd04049cd8baf9a2cde4205d6",
                    "function": {"name": "schedule_tasks_with_calendar"},
                    "type": "function",
                }
            ]
        },
        # Arguments coming in chunks
        {"tool_calls": [{"index": 0, "function": {"arguments": '{"task_description'}}]},
        {"tool_calls": [{"index": 0, "function": {"arguments": '":"create an'}}]},
        {
            "tool_calls": [
                {"index": 0, "function": {"arguments": " engaging gradio ui"}}
            ]
        },
        {
            "tool_calls": [
                {
                    "index": 0,
                    "function": {
                        "arguments": ' for yuga","calendar_file_content":"test123"}'
                    },
                }
            ]
        },
    ]

    logger.debug("Processing streaming deltas...")
    for i, delta in enumerate(sample_deltas):
        logger.debug(f"  Delta {i+1}: {delta}")
        assembler.process_delta(delta)

        # Show debug info after each delta
        debug_info = assembler.debug_info()
        logger.debug(
            f"    -> Tool calls: {debug_info['total_tool_calls']}, Completed: {debug_info['completed_tool_calls']}"
        )

        if debug_info["tool_calls_detail"]:
            for idx, detail in debug_info["tool_calls_detail"].items():
                logger.debug(
                    f"    -> Tool {idx}: {detail['function_name']}, Args valid: {detail['is_json_valid']}"
                )
                logger.debug(f"       Args preview: {detail['arguments_preview']}")

    completed_calls = assembler.get_completed_tool_calls()
    logger.info(f"✅ Completed tool calls: {len(completed_calls)}")

    for i, tool_call in enumerate(completed_calls):
        logger.debug(f"Tool Call {i+1}:")
        logger.debug(f"  ID: {tool_call['id']}")
        logger.debug(f"  Function: {tool_call['function']['name']}")
        logger.debug(f"  Arguments: {tool_call['function']['arguments']}")

        # Try to parse arguments
        try:
            args = json.loads(tool_call["function"]["arguments"])
            logger.debug(f"  ✅ JSON Valid: {args}")

        except json.JSONDecodeError as e:
            logger.error(f"  ❌ JSON Invalid: {e}")
            raise AssertionError(f"Tool call {i+1} has invalid JSON: {e}")

    # Verify we got expected results
    assert len(completed_calls) > 0, "Should have at least one completed tool call"

    logger.pass_test("Normal tool call assembly works correctly")


def test_broken_json():
    """Test with broken JSON to see how we handle it"""

    logger.start_test("Testing Broken JSON Handling")

    assembler = ToolCallAssembler()

    # Simulate incomplete/broken JSON
    broken_deltas = [
        {
            "tool_calls": [
                {
                    "index": 0,
                    "id": "test-broken",
                    "function": {"name": "schedule_tasks_with_calendar"},
                    "type": "function",
                }
            ]
        },
        {
            "tool_calls": [
                {"index": 0, "function": {"arguments": '{"task_description":"test'}}
            ]
        },
        # Missing closing quote and brace - should be invalid JSON
    ]

    for delta in broken_deltas:
        assembler.process_delta(delta)

    completed_calls = assembler.get_completed_tool_calls()
    debug_info = assembler.debug_info()

    logger.debug(f"Broken JSON Test Results:")
    logger.debug(f"  Total tool calls: {debug_info['total_tool_calls']}")
    logger.debug(f"  Completed (valid JSON): {len(completed_calls)}")
    logger.debug(f"  Expected: 0 completed (due to broken JSON)")

    for idx, detail in debug_info["tool_calls_detail"].items():
        logger.debug(f"  Tool {idx}: JSON valid = {detail['is_json_valid']}")
        logger.debug(f"    Args: {detail['arguments_preview']}")

    # Should be 0 due to invalid JSON
    expected_completed = 0
    assert (
        len(completed_calls) == expected_completed
    ), f"Expected {expected_completed} completed calls due to broken JSON, got {len(completed_calls)}"

    logger.pass_test("Broken JSON handling works correctly")


if __name__ == "__main__":
    logger.section("Tool Call Assembly Test Suite")
    logger.info("Testing the isolated tool call assembly logic...")

    # Create test results tracker
    results = create_test_results(logger)

    # Run tests using the standardized approach
    results.run_test("normal_assembly", test_tool_call_assembly)
    results.run_test("broken_json_handling", test_broken_json)

    # Generate summary and exit with appropriate code
    all_passed = results.summary()

    if all_passed:
        logger.info(
            "🎉 All tests passed! Tool call assembly logic is working correctly."
        )

    else:
        logger.error("💥 Some tests failed. Check the logic above.")

    sys.exit(0 if all_passed else 1)
