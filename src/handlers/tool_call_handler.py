import json
import re
import asyncio
from typing import Dict, List, Any, Optional
from utils.logging_config import setup_logging, get_logger

# Initialize logging
setup_logging()
logger = get_logger(__name__)


class ToolCallAssembler:
    """Handles streaming tool call assembly from API responses"""

    def __init__(self):
        self.tool_calls: Dict[int, Dict[str, Any]] = {}
        self.reset()

    def reset(self):
        """Reset the assembler for a new conversation"""
        self.tool_calls = {}

    def process_delta(self, delta: Dict[str, Any]) -> None:
        """Process a single delta from streaming response"""
        if "tool_calls" not in delta:
            return

        for tool_call_delta in delta["tool_calls"]:
            index = tool_call_delta.get("index", 0)

            # Initialize tool call if not exists
            if index not in self.tool_calls:
                self.tool_calls[index] = {
                    "id": "",
                    "type": "function",
                    "function": {"name": "", "arguments": ""},
                }

            # Update tool call components
            if "id" in tool_call_delta:
                self.tool_calls[index]["id"] = tool_call_delta["id"]
            if "type" in tool_call_delta:
                self.tool_calls[index]["type"] = tool_call_delta["type"]
            if "function" in tool_call_delta:
                if "name" in tool_call_delta["function"]:
                    self.tool_calls[index]["function"]["name"] = tool_call_delta[
                        "function"
                    ]["name"]
                if "arguments" in tool_call_delta["function"]:
                    # Append arguments (they come in chunks)
                    self.tool_calls[index]["function"]["arguments"] += tool_call_delta[
                        "function"
                    ]["arguments"]

    def get_completed_tool_calls(self) -> List[Dict[str, Any]]:
        """Get list of completed tool calls"""
        completed = []
        for tool_call in self.tool_calls.values():
            # Check if tool call is complete (has name and valid JSON arguments)
            if tool_call["function"]["name"] and tool_call["function"]["arguments"]:
                try:
                    # Validate JSON arguments
                    json.loads(tool_call["function"]["arguments"])
                    completed.append(tool_call)
                except json.JSONDecodeError as e:
                    logger.warning(
                        f"Tool call {tool_call['id']} has invalid JSON arguments: {e}"
                    )
                    logger.debug(f"Arguments: {tool_call['function']['arguments']}")

                    # Enhanced debugging for character 805 issue
                    args = tool_call["function"]["arguments"]
                    error_pos = getattr(e, "pos", 804)  # Get error position

                    if error_pos > 0:
                        # Show context around the error
                        start = max(0, error_pos - 50)
                        end = min(len(args), error_pos + 50)
                        context = args[start:end]

                        logger.error(f"JSON Error Context (around char {error_pos}):")
                        logger.error(
                            f"  Before error: '{args[max(0, error_pos-20):error_pos]}'"
                        )
                        logger.error(
                            f"  At error: '{args[error_pos:error_pos+1] if error_pos < len(args) else 'END'}'"
                        )
                        logger.error(
                            f"  After error: '{args[error_pos+1:error_pos+21] if error_pos < len(args) else ''}'"
                        )
                        logger.error(f"  Full context: '{context}'")

                        # Check if it's the calendar data causing issues
                        if "calendar_file_content" in args:
                            # Find where calendar data starts and ends
                            cal_start = args.find('"calendar_file_content":"')
                            if cal_start != -1:
                                cal_data_start = cal_start + len(
                                    '"calendar_file_content":"'
                                )
                                # Look for the closing quote
                                cal_end = args.find('"', cal_data_start + 1)
                                if cal_end != -1:
                                    logger.error(
                                        f"Calendar data length: {cal_end - cal_data_start}"
                                    )
                                    logger.error(
                                        f"Calendar data starts at: {cal_data_start}"
                                    )
                                    logger.error(f"Calendar data ends at: {cal_end}")
                                    logger.error(
                                        f"Error position relative to cal data: {error_pos - cal_data_start}"
                                    )
                                else:
                                    logger.error("Calendar data has no closing quote!")
                            else:
                                logger.error(
                                    "No calendar_file_content found in arguments"
                                )

                    # Try to repair the JSON by attempting common fixes
                    try:
                        repaired_args = self._attempt_json_repair(args)
                        if repaired_args:
                            json.loads(repaired_args)  # Test if repair worked
                            logger.info(
                                f"Successfully repaired JSON for tool call {tool_call['id']}"
                            )
                            # Update the tool call with repaired arguments
                            tool_call["function"]["arguments"] = repaired_args
                            completed.append(tool_call)
                            continue
                    except:
                        logger.debug("JSON repair attempt failed")

        return completed

    def _attempt_json_repair(self, broken_json: str) -> str:
        """Attempt to repair common JSON issues"""
        try:
            # Common issue: Missing closing brace
            if not broken_json.strip().endswith("}"):
                return broken_json.strip() + "}"

            # Common issue: Malformed calendar data causing JSON breaks
            # The error is likely around character 795 in the base64 data
            if '"calendar_file_content":"' in broken_json:
                # Try to find and fix the calendar field
                start_pattern = '"calendar_file_content":"'
                start_idx = broken_json.find(start_pattern)

                if start_idx != -1:
                    content_start = start_idx + len(start_pattern)

                    # Find the actual end of the JSON by looking for the pattern
                    # that should follow calendar content: "} or ",
                    remaining = broken_json[content_start:]

                    # Look for what appears to be a duplicate task_description field
                    # This indicates where the JSON got corrupted
                    duplicate_pattern = r'"[\s\S]*?\{\s*"task_description"'
                    match = re.search(duplicate_pattern, remaining)

                    if match:
                        # The base64 data should end before this match
                        clean_end_pos = content_start + match.start()

                        # Extract the clean calendar data (everything before the corrupted part)
                        clean_calendar_data = (
                            broken_json[content_start:clean_end_pos]
                            .rstrip('"')
                            .rstrip()
                        )

                        # Extract the task description from the duplicate section
                        dup_start = content_start + match.start()
                        dup_content = broken_json[dup_start:]

                        # Find the actual JSON structure in the duplicate content
                        dup_json_start = dup_content.find('{"task_description"')
                        if dup_json_start != -1:
                            clean_rest = dup_content[dup_json_start:]

                            # Remove any trailing garbage that might cause JSON issues
                            if not clean_rest.endswith("}"):
                                # Try to find the proper ending
                                brace_count = 0
                                proper_end = -1
                                for i, char in enumerate(clean_rest):
                                    if char == "{":
                                        brace_count += 1
                                    elif char == "}":
                                        brace_count -= 1
                                        if brace_count == 0:
                                            proper_end = i + 1
                                            break

                                if proper_end != -1:
                                    clean_rest = clean_rest[:proper_end]
                                else:
                                    clean_rest = clean_rest.rstrip() + "}"

                            # Parse the clean rest to extract just the fields we need
                            try:
                                rest_obj = json.loads(clean_rest)
                                task_desc = rest_obj.get("task_description", "")

                                # Reconstruct the proper JSON
                                repaired_obj = {
                                    "task_description": task_desc,
                                    "calendar_file_content": clean_calendar_data,
                                }

                                repaired = json.dumps(repaired_obj)
                                logger.debug(
                                    f"Successfully reconstructed JSON with task: {task_desc[:50]}..."
                                )
                                logger.debug(
                                    f"Calendar data length: {len(clean_calendar_data)}"
                                )
                                return repaired

                            except json.JSONDecodeError as e:
                                logger.debug(
                                    f"Failed to parse extracted duplicate section: {e}"
                                )
                                # Fallback to simple reconstruction
                                repaired = f'{{"task_description":"","calendar_file_content":"{clean_calendar_data}"}}'
                                logger.debug(
                                    f"Fallback repair with calendar data length: {len(clean_calendar_data)}"
                                )
                                return repaired

                    # Alternative: Look for more traditional closing patterns
                    # Find where the base64 data properly ends with quote+comma or quote+brace
                    for i, char in enumerate(remaining):
                        if char == '"':
                            # Check what follows the quote
                            next_chars = (
                                remaining[i : i + 3]
                                if i + 3 <= len(remaining)
                                else remaining[i:]
                            )
                            if next_chars.startswith('",') or next_chars.startswith(
                                '"}'
                            ):
                                # This looks like a proper end
                                calendar_data = remaining[:i]
                                rest = remaining[i:]
                                repaired = (
                                    broken_json[:content_start] + calendar_data + rest
                                )
                                logger.debug(
                                    f"Pattern-based repair: calendar data length {len(calendar_data)}"
                                )
                                return repaired

            # If calendar repair didn't work, try other common fixes
            # Remove any stray characters that might have been inserted
            cleaned = re.sub(
                r"[^\x20-\x7E]", "", broken_json
            )  # Remove non-printable chars
            if cleaned != broken_json:
                logger.debug("Attempted to remove non-printable characters")
                return cleaned

            # Last resort: Try to extract valid JSON from the string
            # Look for the first { and try to find matching }
            first_brace = broken_json.find("{")
            if first_brace != -1:
                brace_count = 0
                for i in range(first_brace, len(broken_json)):
                    if broken_json[i] == "{":
                        brace_count += 1
                    elif broken_json[i] == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            candidate = broken_json[first_brace : i + 1]
                            try:
                                json.loads(candidate)
                                logger.debug(
                                    f"Extracted valid JSON segment of length {len(candidate)}"
                                )
                                return candidate
                            except:
                                continue

            return None
        except Exception as e:
            logger.debug(f"JSON repair attempt failed: {e}")
            return None

    def debug_info(self) -> Dict[str, Any]:
        """Get debug information about current tool calls"""
        info = {
            "total_tool_calls": len(self.tool_calls),
            "completed_tool_calls": len(self.get_completed_tool_calls()),
            "tool_calls_detail": {},
        }

        for index, tool_call in self.tool_calls.items():
            info["tool_calls_detail"][index] = {
                "id": tool_call["id"],
                "function_name": tool_call["function"]["name"],
                "arguments_length": len(tool_call["function"]["arguments"]),
                "arguments_preview": tool_call["function"]["arguments"][:100] + "..."
                if len(tool_call["function"]["arguments"]) > 100
                else tool_call["function"]["arguments"],
                "is_json_valid": self._is_valid_json(
                    tool_call["function"]["arguments"]
                ),
            }

        return info

    def _is_valid_json(self, json_str: str) -> bool:
        """Check if string is valid JSON"""
        try:
            json.loads(json_str)
            return True
        except:
            return False


class ToolCallProcessor:
    """Processes completed tool calls"""

    def __init__(self, mcp_client):
        self.mcp_client = mcp_client
        self.loop = None
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

    def process_tool_calls(self, tool_calls: List[Dict[str, Any]], message: str) -> str:
        """Process a list of tool calls and return response text"""
        if not tool_calls:
            return ""

        response_parts = []

        for tool_call in tool_calls:
            logger.info(f"Processing tool call: {tool_call}")

            try:
                # Extract function details
                function_name = tool_call.get("function", {}).get("name", "")
                function_args_str = tool_call.get("function", {}).get("arguments", "{}")

                if function_name == "schedule_tasks_with_calendar":
                    result = self._process_scheduling_tool(function_args_str, message)
                    response_parts.append(result)
                else:
                    logger.debug(f"Ignoring non-scheduling tool: {function_name}")

            except Exception as e:
                logger.error(f"Error processing tool call: {e}")
                response_parts.append(f"\n\n❌ **Error processing tool call:** {str(e)}")

        return "".join(response_parts)

    def _process_scheduling_tool(self, function_args_str: str, message: str) -> str:
        """Process scheduling tool call"""
        try:
            # Parse arguments
            args = json.loads(function_args_str)
            task_description = args.get("task_description", "")
            calendar_content = args.get("calendar_file_content", "none")

            # Extract calendar data from message if available (override args)
            calendar_match = re.search(r"\[CALENDAR_DATA:([^\]]+)\]", message)
            if calendar_match:
                calendar_content = calendar_match.group(1)
                logger.debug("Found calendar data in message, overriding args")

            logger.info(f"Calling MCP scheduling tool with task: {task_description}")

            # Call the scheduling tool
            result = self.loop.run_until_complete(
                self.mcp_client.call_scheduling_tool(task_description, calendar_content)
            )

            logger.info(
                f"MCP tool completed with status: {result.get('status', 'unknown')}"
            )

            return self._format_scheduling_result(result, task_description)

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in tool arguments: {e}")
            logger.debug(f"Raw arguments: {function_args_str}")
            return f"\n\n❌ **Error parsing tool arguments:** {str(e)}\n\nRaw arguments preview: {function_args_str[:200]}..."
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return f"\n\n❌ **Error processing scheduling request:** {str(e)}"

    def _format_scheduling_result(
        self, result: Dict[str, Any], task_description: str
    ) -> str:
        """Format the scheduling result for display"""
        if result.get("status") == "success":
            schedule = result.get("schedule", [])
            calendar_entries = result.get("calendar_entries", [])

            return f"""

📅 **Schedule Generated Successfully!**

**Task:** {task_description}
**Calendar Events Processed:** {len(calendar_entries)}
**Total Scheduled Items:** {len(schedule)}

**Summary:**
- ✅ Existing calendar events preserved at original times
- 🆕 New tasks optimized around existing commitments
- ⏰ All scheduling respects business hours (9:00-18:00)
- 📋 Complete schedule integration

To see the detailed schedule, ask me to "show the schedule as a table" or "format the schedule results".
"""
        elif result.get("status") == "timeout":
            return f"""

⏰ **Scheduling Analysis In Progress**

The schedule optimizer is still working on your complex task: "{task_description}"

This indicates a sophisticated scheduling challenge with multiple constraints. The system is finding the optimal arrangement for your tasks around existing calendar commitments.

You can check back in a few moments or try with a simpler task description.
"""
        else:
            error_msg = result.get("error", "Unknown error")
            return f"""

❌ **Scheduling Error**

I encountered an issue while processing your scheduling request: {error_msg}

Please try:
- Simplifying your task description
- Checking if you have calendar conflicts
- Ensuring your .ics file is valid (if uploaded)
"""


def create_tool_call_handler(mcp_client):
    """Factory function to create a complete tool call handler"""
    assembler = ToolCallAssembler()
    processor = ToolCallProcessor(mcp_client)

    return assembler, processor
