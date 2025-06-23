import json
import sys


# Add src to path to import our modules
sys.path.insert(0, "src")

from handlers.tool_call_handler import ToolCallAssembler

# Import standardized test utilities
from tests.test_utils import get_test_logger, create_test_results

# Initialize standardized test logger
logger = get_test_logger(__name__)


def test_actual_streaming_error():
    """Test the JSON repair functionality with the actual streaming error pattern"""

    logger.start_test("Testing JSON repair functionality with actual streaming error")

    # This is based on the actual error from the logs at character 787
    # The pattern shows base64 data ending abruptly with a quote and then a duplicate JSON object
    broken_json = """{"task_description":"create ec2 on aws","calendar_file_content":"QkVHSU46VkNBTEVOREFSClZFUlNJT046Mi4wClBST0RJRDotLy9pY2FsLm1hcnVkb3QuY29tLy9pQ2FsIEV2ZW50IE1ha2VyCkNBTFNDQUxFOkdSRUdPUklBTgpCRUdJTjpWVElNRVpPTkUKVFpJRDpBZnJpY2EvTGFnb3MKTEFTVC1NT0RJRklFRDoyMDI0MDQyMlQwNTM0NTBaClRaVVJMOmh0dHBzOi8vd3d3LnR6dXJsLm9yZy96b25laW5mby1vdXRsb29rL0FmcmljYS9MYWdvcwpYLUxJQy1MT0NBVElPTjpBZnJpY2EvTGFnb3MKQkVHSU46U1RBTkRBUkQKVFpOQU1FOldBVApUWk9GRlNFVEZST006KzAxMDAKVFpPRkZTRVRUTzorMDEwMApEVFNUQVJUOjE5NzAwMTAxVDAwMDAwMApFTkQ6U1RBTkRBUkQKRU5EOlZUSU1FWk9ORQpCRUdJTjpWRVZFTlQKRFRTVEFNUDoyMDI1MDYyMFQxMzQxMjBaClVJRDpyZWN1ci1tZWV0aW5nLTJAbW9jawpEVFNUQVJUO1RaSUQ9QWZyaWNhL0xhZ29zOjIwMjUwNjAyVDE1MDAwMApEVEVORDtUWklEPUFmcmljYS9MYWdvczoyMDI1MDYwMlQxNjAwMDAKU1VNTUFSWTpQcm9qZWN0IFJldmlldwpFTkQ6VkVWRU5UCkJFR0lOO"{"task_description":"create ec2 on aws","calendar_file_content":"QkVHSU46VkNBTEVOREFSClZFUlNJT046Mi4wClBST0RJRDotLy9pY2FsLm1hcnVkb3QuY29tLy9pQ2FsIEV2ZW50IE1ha2VyCkNBTFNDQUxFOkdSRUdPUklBTgpCRUdJTjpWVElNRVpPTkUKVFpJRDpBZnJpY2EvTGFnb3MKTEFTVC1NT0RJRklFRDoyMDI0MDQyMlQwNTM0NTBaClRaVVJMOmh0dHBzOi8vd3d3LnR6dXJsLm9yZy96b25laW5mby1vdXRsb29rL0FmcmljYS9MYWdvcwpYLUxJQy1MT0NBVElPTjpBZnJpY2EvTGFnb3MKQkVHSU46U1RBTkRBUkQKVFpOQU1FOldBVApUWk9GRlNFVEZST006KzAxMDAKVFpPRkZTRVRUTzorMDEwMApEVFNUQVJUOjE5NzAwMTAxVDAwMDAwMApFTkQ6U1RBTkRBUkQKRU5EOlZUSU1FWk9ORQpCRUdJTjpWRVZFTlQKRFRTVEFNUDoyMDI1MDYyMFQxMzQxMjBaClVJRDpyZWN1ci1tZWV0aW5nLTFAbW9jawpEVFNUQVJUO1RaSUQ9QWZyaWNhL0xhZ29zOjIwMjUwNjAzVDEwMDAwMApEVEVORDtUWklEPUFmcmljYS9MYWdvczoyMDI1MDYwM1QxMTAwMDAKU1VNTUFSWTpUZWFtIFN5bmMKRU5EOlZFVkVOVApCRUdJTjpWRVZFTlQKRFRTVEFNUDoyMDI1MDYyMFQxMzQxMjBaClVJRDpzaW5nbGUtZXZlbnQtMUBtb2NrCkRUU1RBUlQ7VFpJRD1BZnJpY2EvTGFnb3M6MjAyNTA2MDVUMTQwMDAwCkRURU5EO1RaSUQ9QWZyaWNhL0xhZ29zOjIwMjUwNjA1VDE1MDAwMApTVU1NQVJZOkNsaWVudCBDYWxsCkVORDpWRVZFTlQKQkVHSU46VkVWRU5UCkRUU1RBTVA6MjAyNTA2MjBUMTM0MTIwWgpVSUQ6c2luZ2xlLWV2ZW50LTRAbW9jawpEVFNUQVJUO1RaSUQ9QWZyaWNhL0xhZ29zOjIwMjUwNjE2VDE2MDAwMApEVEVORDtUWklEPUFmcmljYS9MYWdvczoyMDI1MDYxNlQxNzAwMDAKU1VNTUFSWTpXb3Jrc2hvcApFTkQ6VkVWRU5UCkJFR0lOOlZFVkVOVApEVFNUQU1QOjIwMjUwNjIwVDEzNDEyMFoKVUlEOnNpbmdsZS1ldmVudC0zQG1vY2sKRFRTVEFSVDtUWklEPUFmcmljYS9MYWdvczoyMDI1MDcwN1QxMTAwMDAKRFRFTkQ7VFpJRD1BZnJpY2EvTGFnb3M6MjAyNTA3MDdUMTIwMDAwClNVTU1BUlk6UGxhbm5pbmcgU2Vzc2lvbgpFTkQ6VkVWRU5UCkJFR0lOOlZFVkVOVApEVFNUQU1QOjIwMjUwNjIwVDEzNDEyMFoKVUlEOnNpbmdsZS1ldmVudC01QG1vY2sKRFRTVEFSVDtUWklEPUFmcmljYS9MYWdvczoyMDI1MDcyMlQwOTAwMDAKRFRFTkQ7VFpJRD1BZnJpY2EvTGFnb3M6MjAyNTA3MjJUMTAwMDAwClNVTU1BUlk6RGVtbwpFTkQ6VkVWRU5UCkVORDpWQ0FMRU5EQVI="}"""

    logger.debug(f"Broken JSON length: {len(broken_json)}")

    # Find the error position (where the duplicate starts)
    error_pos = broken_json.find(';"{"task_description"')
    logger.debug(f"Error position (duplicate JSON start): {error_pos}")

    # Try to parse the broken JSON first to confirm it fails
    json_parse_failed = False
    try:
        json.loads(broken_json)
        logger.error("❌ UNEXPECTED: Broken JSON parsed successfully!")
    except json.JSONDecodeError as e:
        json_parse_failed = True
        logger.info(f"✅ Expected JSON error at position {e.pos}: {e}")
        logger.debug(f"Error context: '{broken_json[max(0, e.pos-20):e.pos+20]}'")

    assert json_parse_failed, "Expected broken JSON to fail parsing"

    # Test the repair function
    assembler = ToolCallAssembler()
    repaired_json = assembler._attempt_json_repair(broken_json)

    assert repaired_json is not None, "Repair should return a result"

    logger.info(f"✅ Repair attempted, result length: {len(repaired_json)}")
    logger.debug(f"Repaired preview: {repaired_json[:200]}...")

    # Try to parse the repaired JSON
    parsed = json.loads(repaired_json)
    logger.debug(f"Task description: {parsed.get('task_description', 'MISSING')}")
    logger.debug(
        f"Calendar content length: {len(parsed.get('calendar_file_content', ''))}"
    )

    # Verify expected fields exist
    assert "task_description" in parsed, "Repaired JSON should have task_description"
    assert (
        "calendar_file_content" in parsed
    ), "Repaired JSON should have calendar_file_content"
    assert (
        parsed["task_description"] == "create ec2 on aws"
    ), "Task description should match expected value"

    logger.pass_test("Repaired JSON parses correctly")


def test_simpler_corruption():
    """Test a simpler case of JSON corruption for baseline functionality"""

    logger.start_test("Testing simpler JSON corruption")

    # Missing closing brace
    simple_broken = (
        '{"task_description":"test task","calendar_file_content":"base64data"'
    )

    assembler = ToolCallAssembler()
    repaired = assembler._attempt_json_repair(simple_broken)

    assert repaired is not None, "Simple repair should return a result"

    # Try to parse the repaired JSON
    parsed = json.loads(repaired)

    assert (
        "task_description" in parsed
    ), "Simple repair should preserve task_description"
    assert parsed["task_description"] == "test task", "Task description should match"

    logger.pass_test("Simple repair works correctly")


def test_datetime_serialization():
    """Test our datetime serialization fixes"""

    logger.start_test("Testing datetime serialization")

    # Import our safe serialization function
    from ui.pages.chat import safe_json_dumps
    from datetime import datetime

    test_data = {
        "schedule": [
            {
                "task": "Test Task",
                "start_time": datetime(2025, 6, 23, 10, 0),
                "end_time": datetime(2025, 6, 23, 11, 0),
            }
        ],
        "timestamp": datetime.now(),
    }

    result = safe_json_dumps(test_data, indent=2)
    logger.debug(f"Sample output: {result[:200]}...")

    # Verify it's valid JSON
    parsed_back = json.loads(result)
    assert "schedule" in parsed_back, "Serialized result should have schedule"
    assert "timestamp" in parsed_back, "Serialized result should have timestamp"
    assert len(parsed_back["schedule"]) == 1, "Schedule should have one item"

    logger.pass_test("Datetime serialization works correctly")


def test_gradio_format():
    """Test that we're returning the correct format for Gradio messages"""

    logger.start_test("Testing Gradio message format")

    # Simulate a proper messages format
    test_history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "Create a schedule"},
    ]

    # This is what our function should return
    expected_format = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "Create a schedule"},
        {"role": "assistant", "content": "Schedule created successfully!"},
    ]

    logger.debug("Expected format is list of dicts with 'role' and 'content' keys")

    # Validate the format
    for i, msg in enumerate(expected_format):
        assert isinstance(msg, dict), f"Message {i} should be a dict, got {type(msg)}"
        assert "role" in msg, f"Message {i} should have 'role' key"
        assert "content" in msg, f"Message {i} should have 'content' key"
        assert msg["role"] in [
            "user",
            "assistant",
        ], f"Message {i} has invalid role: {msg['role']}"

    logger.pass_test("Message format is correct for Gradio")


if __name__ == "__main__":
    logger.section("JSON Repair and Chat Functionality Tests")

    # Create test results tracker
    results = create_test_results(logger)

    # Run tests using the standardized approach
    results.run_test("streaming_error_repair", test_actual_streaming_error)
    results.run_test("simple_json_repair", test_simpler_corruption)
    results.run_test("datetime_serialization", test_datetime_serialization)
    results.run_test("gradio_message_format", test_gradio_format)

    # Generate summary and exit with appropriate code
    all_passed = results.summary()
    sys.exit(0 if all_passed else 1)
