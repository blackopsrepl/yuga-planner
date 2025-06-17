import os
from dataclasses import dataclass
import uuid
import time
import asyncio

from utils.extract_calendar import extract_ical_entries
from factory.data_provider import generate_mcp_data
from services.schedule_service import ScheduleService


@dataclass
class MCPProcessingResult:
    user_message: str
    file: str
    calendar_entries: list = None
    error: str = None
    solved_task_df: object = None
    status: str = None
    score: object = None


async def process_message_and_attached_file(file_path: str, message_body: str) -> dict:
    """
    Store the last chat message and attached file, echo the message, extract calendar entries, generate tasks, solve, and poll for the solution.
    Args:
        file_path (str): Path to the attached file
        message_body (str): The body of the last chat message, which contains the task description
    Returns:
        dict: Contains confirmation, file info, calendar entries, error, and solved schedule info
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
    if error:
        result = MCPProcessingResult(
            user_message=f"Received your message: {message_body}",
            file=os.path.basename(file_path),
            error=f"File is not a valid calendar file: {error}",
        )
        return result.__dict__

    # Generate MCP DataFrame
    df = await generate_mcp_data(entries, message_body)
    if df is None or df.empty:
        result = MCPProcessingResult(
            user_message=f"Received your message: {message_body}",
            file=os.path.basename(file_path),
            calendar_entries=entries,
            error="Failed to generate MCP data.",
        )
        return result.__dict__

    # Build state_data for the solver
    state_data = {
        "task_df_json": df.to_json(orient="split"),
        "employee_count": 1,
        "days_in_schedule": 365,
    }
    job_id = str(uuid.uuid4())
    (
        emp_df,
        solved_task_df,
        new_job_id,
        status,
        state_data,
    ) = await ScheduleService.solve_schedule_from_state(state_data, job_id, debug=True)

    # Poll for the solution until the status string does not contain 'Solving'
    max_wait = 30  # seconds
    interval = 0.5
    waited = 0
    final_task_df = None
    final_status = None
    final_score = None
    solved = False
    while waited < max_wait:
        (
            _,
            polled_task_df,
            _,
            polled_status,
            solved_schedule,
        ) = ScheduleService.poll_solution(new_job_id, None, debug=True)
        if polled_status and "Solving" not in polled_status:
            final_task_df = polled_task_df
            final_status = polled_status
            final_score = getattr(solved_schedule, "score", None)
            solved = True
            break
        await asyncio.sleep(interval)
        waited += interval

    result = MCPProcessingResult(
        user_message=f"Received your message: {message_body}",
        file=os.path.basename(file_path),
        calendar_entries=entries,
        solved_task_df=final_task_df.to_dict(orient="records")
        if final_task_df is not None
        else None,
        status=final_status,
        score=final_score,
        error=None if solved else "Solver did not finish within the timeout",
    )
    return result.__dict__
