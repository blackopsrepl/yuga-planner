import os
from dataclasses import dataclass

from utils.extract_calendar import extract_ical_entries
from factory.data_provider import generate_mcp_data


@dataclass
class MCPProcessingResult:
    user_message: str
    file: str
    calendar_entries: list = None
    error: str = None


async def process_message_and_attached_file(file_path: str, message_body: str) -> dict:
    """
    Store the last chat message and attached file, echo the message, and extract calendar entries if possible.
    Args:
        file_path (str): Path to the attached file
        message_body (str): The body of the last chat message, which contains the task description
    Returns:
        dict: Contains confirmation, file info, and calendar entries or error
    """
    try:
        with open(file_path, "rb") as f:
            file_bytes = f.read()

    except Exception as e:
        result = MCPProcessingResult(
            user_message="",
            file="",
            calendar_entries=[],
            error=f"Failed to read file: {e}",
        )
        return result.__dict__

    # Try to extract calendar entries
    entries, error = extract_ical_entries(file_bytes)

    input = MCPProcessingResult(
        user_message=f"Received your message: {message_body}",
        file=os.path.basename(file_path),
        calendar_entries=entries,
        error=error,
    )

    schedule = await generate_mcp_data(entries, message_body)

    if error:
        result = MCPProcessingResult(
            user_message=f"Received your message: {message_body}",
            file=os.path.basename(file_path),
            error=f"File is not a valid calendar file: {error}",
        )
        return result.__dict__

    result = MCPProcessingResult(
        user_message=f"Received your message: {message_body}",
        file=os.path.basename(file_path),
        calendar_entries=entries,
    )
    return result.__dict__
