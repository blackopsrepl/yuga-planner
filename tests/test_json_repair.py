import sys, json

# Add src to path to import our modules
sys.path.insert(0, "src")

from datetime import datetime

from handlers.tool_call_handler import ToolCallAssembler
from tests.test_utils import get_test_logger
from ui.pages.chat import safe_json_dumps

# Initialize standardized test logger
logger = get_test_logger(__name__)


def test_actual_streaming_error():
    """Test the JSON repair functionality with the actual streaming error pattern"""
    logger.start_test("Testing JSON repair functionality with actual streaming error")

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
    """Test that user_message returns the correct Gradio message format."""
    logger.start_test("Testing Gradio message format via user_message")

    from ui.pages.chat import user_message

    # Simulate a proper messages format
    test_history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]

    message = "Create a schedule"
    calendar_file_obj = None  # No file for this test

    # Call the function under test
    _, new_history, *_ = user_message(message, test_history, calendar_file_obj)

    # The new message should be appended
    assert isinstance(new_history, list), "History should be a list"
    assert len(new_history) == 3, f"Expected 3 messages, got {len(new_history)}"

    last_msg = new_history[-1]

    assert isinstance(last_msg, dict), "Last message should be a dict"
    assert last_msg["role"] == "user", "Last message should have role 'user'"
    assert message in last_msg["content"], "Message content should match input"
    assert "content" in last_msg, "Last message should have 'content' key"

    logger.pass_test("user_message returns correct Gradio message format")


def test_already_valid_json():
    """Test that valid JSON is returned unchanged."""
    logger.start_test("Testing already valid JSON (should be unchanged)")
    valid_json = '{"task_description":"ok","calendar_file_content":"abc"}'
    assembler = ToolCallAssembler()
    repaired = assembler._attempt_json_repair(valid_json)
    assert repaired == valid_json, "Valid JSON should not be changed"
    logger.pass_test("Already valid JSON is unchanged")


def test_non_printable_character_removal():
    """Test that non-printable characters are removed."""
    logger.start_test("Testing non-printable character removal")
    broken = '{"task_description":"ok","calendar_file_content":"abc\x00\x01\x02"}'
    assembler = ToolCallAssembler()
    repaired = assembler._attempt_json_repair(broken)
    assert (
        "\x00" not in repaired and "\x01" not in repaired and "\x02" not in repaired
    ), "Non-printable characters should be removed"
    parsed = json.loads(repaired)
    assert parsed["task_description"] == "ok"
    logger.pass_test("Non-printable characters removed correctly")


def test_fallback_extract_first_valid_json():
    """Test fallback extraction of first valid JSON object."""
    logger.start_test("Testing fallback extraction of first valid JSON object")
    broken = 'garbage before {"task_description":"ok","calendar_file_content":"abc"} garbage after'
    assembler = ToolCallAssembler()
    repaired = assembler._attempt_json_repair(broken)
    parsed = json.loads(repaired)
    assert parsed["task_description"] == "ok"
    logger.pass_test("Fallback extraction of first valid JSON works")


def test_unrecoverable_json_returns_none():
    """Test that unrecoverable JSON returns None."""
    logger.start_test("Testing unrecoverable JSON returns None")
    broken = "this is not json at all"
    assembler = ToolCallAssembler()
    repaired = assembler._attempt_json_repair(broken)
    assert repaired is None, "Unrecoverable JSON should return None"
    logger.pass_test("Unrecoverable JSON returns None as expected")


def test_realworld_corrupted_json():
    """Test repair on a real-world log corruption example (duplicate JSON, partial base64)."""
    logger.start_test("Testing real-world corrupted JSON repair")
    broken = (
        '{"task_description":"foo","calendar_file_content":"abc123"}'
        '{"task_description":"foo","calendar_file_content":"abc123"}'
    )
    assembler = ToolCallAssembler()
    repaired = assembler._attempt_json_repair(broken)
    assert repaired is not None, "Should repair real-world duplicate JSON corruption"
    parsed = json.loads(repaired)
    assert parsed["task_description"] == "foo"
    logger.pass_test("Real-world duplicate JSON repair works")


def test_idempotency():
    """Test that repairing already-repaired JSON is idempotent (no change)."""
    logger.start_test("Testing idempotency of JSON repair")
    valid_json = '{"task_description":"idempotent","calendar_file_content":"abc"}'
    assembler = ToolCallAssembler()
    once = assembler._attempt_json_repair(valid_json)
    twice = assembler._attempt_json_repair(once)
    assert once == twice, "Repair should be idempotent on valid JSON"
    logger.pass_test("Idempotency test passed")
