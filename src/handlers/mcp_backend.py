"""
MCP (Model Context Protocol) Handlers for Yuga Planner

This module provides an MCP tool endpoint for external integrations and is separate from the Gradio UI's workflow.

Key Features:
- Centralized logging integration with debug mode support
- Performance timing for API monitoring
- Comprehensive error handling for external consumers
- Automatic debug mode detection from environment variables

Usage:
    The main endpoint is registered as a Gradio API and can be called by MCP clients:

    POST /api/process_message_and_attached_file
    {
        "file_path": "/path/to/calendar.ics",
        "message_body": "Create tasks for this week's meetings"
    }

Environment Variables:
    YUGA_DEBUG: Set to "true" to enable detailed debug logging for API requests

Logging:
    - Uses centralized logging system from utils.logging_config
    - Respects YUGA_DEBUG environment variable (from CLI flag --debug)
    - Includes performance timing and detailed error information
    - Provides different log levels for production vs development usage
"""

import time

from utils.extract_calendar import extract_ical_entries

from factory.data.provider import generate_mcp_data
from services import ScheduleService, StateService
from factory.data.formatters import schedule_to_dataframe

from utils.logging_config import setup_logging, get_logger, is_debug_enabled

setup_logging()
logger = get_logger(__name__)


async def process_message_and_attached_file(
    file_content: bytes, message_body: str, file_name: str = "calendar.ics"
) -> dict:
    """
    MCP API endpoint for processing calendar files and task descriptions.

    This is a separate workflow from the main Gradio UI and handles external API requests.

    Args:
        file_content (bytes): The actual file content bytes (typically .ics calendar file)
        message_body (str): The body of the last chat message, which contains the task description
        file_name (str): Optional filename for logging purposes
    Returns:
        dict: Contains confirmation, file info, calendar entries, error, and solved schedule info
    """

    # Determine debug mode from environment or default to False for API calls
    debug_mode = is_debug_enabled()

    logger.info("MCP Handler: Processing message with attached file")
    logger.debug("File name: %s", file_name)
    logger.debug(
        "File content size: %d bytes", len(file_content) if file_content else 0
    )
    logger.debug("Message: %s", message_body)
    logger.debug("Debug mode: %s", debug_mode)

    # Track timing for API performance
    start_time = time.time()

    try:
        # Step 1: Extract calendar entries from the file content
        logger.info("Step 1: Extracting calendar entries...")

        if not file_content:
            logger.error("No file content provided")
            return {
                "error": "No file content provided",
                "status": "no_file_content",
                "timestamp": time.time(),
                "processing_time_seconds": time.time() - start_time,
            }

        calendar_entries, error = extract_ical_entries(file_content)

        if error:
            logger.error("Failed to extract calendar entries: %s", error)
            return {
                "error": f"Failed to extract calendar entries: {error}",
                "status": "calendar_parse_failed",
                "timestamp": time.time(),
                "processing_time_seconds": time.time() - start_time,
            }

        logger.info("Extracted %d calendar entries", len(calendar_entries))

        # Log the calendar entries for debugging
        if debug_mode and calendar_entries:
            logger.debug(
                "Calendar entries details: %s",
                [e.get("summary", "No summary") for e in calendar_entries[:5]],
            )

        # Step 2: Generate MCP data (combines calendar and LLM tasks)
        logger.info("Step 2: Generating tasks using MCP data provider...")

        schedule_data = await generate_mcp_data(
            calendar_entries=calendar_entries,
            user_message=message_body,
            project_id="PROJECT",
            employee_count=1,  # MCP uses single user
            days_in_schedule=365,
        )

        logger.info("Generated schedule with %d total tasks", len(schedule_data))

        # Step 3: Convert to format needed for solving
        logger.info("Step 3: Preparing schedule for solving...")

        # Create state data format expected by ScheduleService
        state_data = {
            "task_df_json": schedule_data.to_json(orient="split"),
            "employee_count": 1,
            "days_in_schedule": 365,
        }

        # Step 4: Start solving the schedule
        logger.info("Step 4: Starting schedule solver...")

        (
            emp_df,
            task_df,
            job_id,
            status,
            state_data,
        ) = await ScheduleService.solve_schedule_from_state(
            state_data=state_data,
            job_id=None,
            debug=debug_mode,  # Respect debug mode for MCP calls
        )

        logger.info("Solver started with job_id: %s", job_id)
        logger.debug("Initial status: %s", status)

        # Step 5: Poll until the schedule is solved
        logger.info("Step 5: Polling for solution...")

        max_polls = 60  # Maximum 60 polls (about 2 minutes)
        poll_interval = 2  # Poll every 2 seconds

        for poll_count in range(max_polls):
            if StateService.has_solved_schedule(job_id):
                solved_schedule = StateService.get_solved_schedule(job_id)

                # Check if we have a valid solution
                if solved_schedule is not None:
                    processing_time = time.time() - start_time
                    logger.info(
                        "Schedule solved after %d polls! (Total time: %.2fs)",
                        poll_count + 1,
                        processing_time,
                    )

                    try:
                        # Convert to final dataframe
                        final_df = schedule_to_dataframe(solved_schedule)

                        # Generate status message
                        status_message = ScheduleService.generate_status_message(
                            solved_schedule
                        )

                        logger.info("Final Status: %s", status_message)

                        # Return comprehensive JSON response
                        response_data = {
                            "status": "success",
                            "message": "Schedule solved successfully",
                            "file_info": {
                                "name": file_name,
                                "size_bytes": len(file_content),
                                "calendar_entries_count": len(calendar_entries),
                            },
                            "calendar_entries": calendar_entries,
                            "solution_status": status_message,
                            "schedule": final_df.to_dict(
                                orient="records"
                            ),  # Convert to list of dicts for JSON
                            "job_id": job_id,
                            "polls_required": poll_count + 1,
                            "processing_time_seconds": processing_time,
                            "timestamp": time.time(),
                            "debug_mode": debug_mode,
                        }

                        logger.debug(
                            "Returning JSON response with %d schedule entries",
                            len(response_data["schedule"]),
                        )
                        return response_data

                    except Exception as e:
                        logger.error(
                            "Error converting schedule to JSON: %s",
                            e,
                            exc_info=debug_mode,
                        )
                        # Return error response instead of raising
                        return {
                            "error": f"Error converting schedule to JSON: {str(e)}",
                            "status": "conversion_failed",
                            "job_id": job_id,
                            "processing_time_seconds": processing_time,
                            "timestamp": time.time(),
                            "debug_mode": debug_mode,
                        }

            if debug_mode:
                logger.debug("Poll %d/%d: Still solving...", poll_count + 1, max_polls)

            time.sleep(poll_interval)

        # If we get here, polling timed out
        processing_time = time.time() - start_time
        logger.warning(
            "Polling timed out after %.2fs - returning partial results", processing_time
        )

        return {
            "status": "timeout",
            "message": "Schedule solving timed out after maximum polls",
            "file_info": {
                "name": file_name,
                "size_bytes": len(file_content),
                "calendar_entries_count": len(calendar_entries),
            },
            "calendar_entries": calendar_entries,
            "job_id": job_id,
            "max_polls_reached": max_polls,
            "processing_time_seconds": processing_time,
            "timestamp": time.time(),
            "debug_mode": debug_mode,
        }

    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(
            "MCP handler error after %.2fs: %s", processing_time, e, exc_info=debug_mode
        )

        return {
            "error": str(e),
            "status": "failed",
            "file_name": file_name,
            "message_body": message_body,
            "processing_time_seconds": processing_time,
            "timestamp": time.time(),
            "debug_mode": debug_mode,
        }
