import logging
from typing import Tuple, Dict, List, Optional

import pandas as pd
import gradio as gr

from state import app_state

from services import (
    LoggingService,
    ScheduleService,
    DataService,
    MockProjectService,
)

# Global logging service instance for UI streaming
logging_service = LoggingService()


async def show_solved(
    state_data, job_id: str, debug: bool = False
) -> Tuple[pd.DataFrame, pd.DataFrame, str, str, object, str]:
    """Handler for solving a schedule from UI state data"""
    # Set up log streaming for solving process
    logging_service.setup_log_streaming()

    logging.info(
        f"🔧 show_solved called with state_data type: {type(state_data)}, job_id: {job_id}"
    )

    # Check if data has been loaded
    if not state_data:
        logging.warning("❌ No data loaded - cannot solve schedule")
        return (
            gr.update(),
            gr.update(),
            job_id,
            "❌ No data loaded. Please click 'Load Data' first to load project data before solving.",
            state_data,
            logging_service.get_streaming_logs(),
        )

    logging.info(f"✅ State data found, proceeding with solve...")

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

        logging.info(f"✅ Solver completed successfully, returning results")

        return (
            emp_df,
            solved_task_df,
            new_job_id,
            status,
            state_data,
            logging_service.get_streaming_logs(),
        )
    except Exception as e:
        logging.error(f"Error in show_solved: {e}")
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
    # Set up log streaming and clear previous logs
    logging_service.setup_log_streaming()
    logging_service.clear_streaming_logs()

    # Initial log message
    logging.info("🚀 Starting data loading process...")

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
        app_state.add_solved_schedule(job_id, None)  # Will be populated when solved

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
        logging.error(f"Error loading data: {e}")
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
            gr.update(),  # log_terminal
        )

    except Exception as e:
        logging.error(f"Error in poll_solution: {e}")
        return (
            gr.update(),
            gr.update(),
            job_id,
            f"Error polling solution: {str(e)}",
            schedule,
            gr.update(),  # log_terminal
        )


async def auto_poll(
    job_id: str, llm_output: dict, debug: bool = False
) -> Tuple[pd.DataFrame, pd.DataFrame, str, str, dict, str]:
    """Handler for automatic polling of updates"""
    try:
        (
            emp_df,
            task_df,
            job_id,
            status_message,
            llm_output,
        ) = await ScheduleService.auto_poll(job_id, llm_output, debug)

        return (
            emp_df,  # employees_table
            task_df,  # schedule_table
            job_id,  # job_id_state
            status_message,  # status_text
            llm_output,  # llm_output_state
            logging_service.get_streaming_logs(),  # log_terminal
        )

    except Exception as e:
        logging.error(f"Error in auto_poll: {e}")
        return (
            gr.update(),
            gr.update(),
            job_id,
            f"Error in auto polling: {str(e)}",
            llm_output,
            logging_service.get_streaming_logs(),  # log_terminal
        )
