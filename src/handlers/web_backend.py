from typing import Tuple
import os

import pandas as pd
import gradio as gr

from utils.logging_config import setup_logging, get_logger

# Initialize logging
setup_logging()
logger = get_logger(__name__)

from services import (
    LoggingService,
    ScheduleService,
    DataService,
    MockProjectService,
    StateService,
)

# Global logging service instance for UI streaming
logging_service = LoggingService()


async def show_solved(
    state_data, job_id: str, debug: bool = False
) -> Tuple[pd.DataFrame, pd.DataFrame, str, str, object, str]:
    """Handler for solving a schedule from UI state data"""
    # Ensure log streaming is set up and respects debug mode
    _ensure_log_streaming_setup(debug)

    logger.info(
        "show_solved called with state_data type: %s, job_id: %s",
        type(state_data),
        job_id,
    )

    # Check if data has been loaded
    if not state_data:
        logger.warning("No data loaded - cannot solve schedule")
        return (
            gr.update(),
            gr.update(),
            job_id,
            "❌ No data loaded. Please click 'Load Data' first to load project data before solving.",
            state_data,
            logging_service.get_streaming_logs(),
        )

    logger.info("State data found, proceeding with solve...")

    try:
        # Use the schedule service to solve the schedule
        (
            emp_df,
            solved_task_df,
            new_job_id,
            status,
            state_data,
        ) = await ScheduleService.solve_schedule_from_state(
            state_data, job_id, debug=debug
        )

        logger.info("Solver completed successfully, returning results")

        return (
            emp_df,
            solved_task_df,
            new_job_id,
            status,
            state_data,
            logging_service.get_streaming_logs(),
        )
    except Exception as e:
        logger.error("Error in show_solved: %s", e)
        return (
            gr.update(),
            gr.update(),
            job_id,
            f"❌ Error solving schedule: {str(e)}",
            state_data,
            logging_service.get_streaming_logs(),
        )


def show_mock_project_content(project_names) -> str:
    """Handler for displaying mock project content"""
    return MockProjectService.show_mock_project_content(project_names)


async def load_data(
    project_source: str,
    file_obj,
    mock_projects,
    employee_count: int,
    days_in_schedule: int,
    llm_output,
    debug: bool = False,
    progress=gr.Progress(),
):
    """
    Handler for data loading from either file uploads or mock projects - streaming version
    Yields intermediate updates for real-time progress
    """
    # Ensure log streaming is set up and clear previous logs
    _ensure_log_streaming_setup(debug)
    logging_service.clear_streaming_logs()

    # Initial log message
    logger.info("Starting data loading process...")
    if debug:
        logger.debug("Debug mode enabled for data loading")

    # Yield initial state
    yield (
        gr.update(),  # employees_table
        gr.update(),  # schedule_table
        gr.update(),  # job_id_state
        "Starting data loading...",  # status_text
        gr.update(),  # llm_output_state
        logging_service.get_streaming_logs(),  # log_terminal
        gr.update(interactive=False),  # solve_btn - keep disabled during loading
    )

    try:
        # Use the data service to load data from sources
        (
            emp_df,
            task_df,
            job_id,
            status_message,
            state_data,
        ) = await DataService.load_data_from_sources(
            project_source,
            file_obj,
            mock_projects,
            employee_count,
            days_in_schedule,
            debug,
        )

        # Store schedule for later use
        StateService.store_solved_schedule(
            job_id, None
        )  # Will be populated when solved

        # Final yield with complete results
        yield (
            emp_df,  # employees_table
            task_df,  # schedule_table
            job_id,  # job_id_state
            status_message,  # status_text
            state_data,  # llm_output_state
            logging_service.get_streaming_logs(),  # log_terminal with accumulated logs
            gr.update(interactive=True),  # solve_btn - enable after successful loading
        )

    except Exception as e:
        logger.error("Error loading data: %s", e)
        yield (
            gr.update(),
            gr.update(),
            gr.update(),
            f"Error loading data: {str(e)}",
            gr.update(),
            logging_service.get_streaming_logs(),  # log_terminal
            gr.update(interactive=False),  # solve_btn - keep disabled on error
        )


def start_timer(job_id, llm_output) -> gr.Timer:
    """Handler for starting the polling timer"""
    return ScheduleService.start_timer(job_id, llm_output)


def poll_solution(
    job_id: str, schedule, debug: bool = False
) -> Tuple[pd.DataFrame, pd.DataFrame, str, str, object, str]:
    """Handler for polling a solution for a given job_id"""
    try:
        (
            emp_df,
            task_df,
            job_id,
            status_message,
            schedule,
        ) = ScheduleService.poll_solution(job_id, schedule, debug)

        return (
            emp_df,
            task_df,
            job_id,
            status_message,
            schedule,
            logging_service.get_streaming_logs(),  # Include logs in polling updates
        )

    except Exception as e:
        logger.error("Error in poll_solution: %s", e)
        return (
            gr.update(),
            gr.update(),
            job_id,
            f"Error polling solution: {str(e)}",
            schedule,
            logging_service.get_streaming_logs(),  # Include logs even on error
        )


async def auto_poll(
    job_id: str, llm_output: dict, debug: bool = False
) -> Tuple[pd.DataFrame, pd.DataFrame, str, str, dict, str]:
    """Handler for auto-polling a solution"""
    try:
        (
            emp_df,
            task_df,
            job_id,
            status_message,
            llm_output,
        ) = await ScheduleService.auto_poll(job_id, llm_output, debug)

        return (
            emp_df,
            task_df,
            job_id,
            status_message,
            llm_output,
            logging_service.get_streaming_logs(),  # Include logs in auto-poll updates
        )

    except Exception as e:
        logger.error("Error in auto_poll: %s", e)
        return (
            gr.update(),
            gr.update(),
            job_id,
            f"Error in auto-polling: {str(e)}",
            llm_output,
            logging_service.get_streaming_logs(),  # Include logs even on error
        )


def _ensure_log_streaming_setup(debug: bool = False) -> None:
    """
    Ensure log streaming is properly set up with current debug settings.
    This helps maintain consistency when debug mode changes at runtime.
    """
    if debug:
        # Force debug mode setup if explicitly requested
        os.environ["YUGA_DEBUG"] = "true"
        setup_logging("DEBUG")

    # Always setup streaming (it will respect current logging level)
    logging_service.setup_log_streaming()

    if debug:
        logger.debug("Log streaming setup completed with debug mode enabled")
