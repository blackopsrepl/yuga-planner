import os, random, uuid, logging
from io import StringIO
from datetime import datetime

from typing import Tuple, Dict, List, Optional

import pandas as pd

import gradio as gr

from factory.data_provider import (
    generate_agent_data,
    DATA_PARAMS,
    TimeTableDataParameters,
    generate_employees,
    generate_employee_availability,
)

from constraint_solvers.timetable.domain import (
    EmployeeSchedule,
    ScheduleInfo,
    Task,
    Employee,
)
from constraint_solvers.timetable.solver import solver_manager

from helpers import schedule_to_dataframe, employees_to_dataframe

# Global state for solved schedules
solved_schedules: Dict[str, EmployeeSchedule] = {}


async def show_solved(
    task_df_json: str, job_id: str, debug: bool = False
) -> Tuple[pd.DataFrame, pd.DataFrame, str, str, object]:
    # Dataframe from JSON debug logging
    if debug:
        logging.info("Task DataFrame JSON received in show_solved: %s", task_df_json)

    if not task_df_json:
        return (
            gr.update(),
            gr.update(),
            None,
            "No schedule to solve. Please load data first.",
            None,
        )

    task_df: pd.DataFrame = pd.read_json(StringIO(task_df_json), orient="split")

    # Log sequence numbers from JSON for debugging
    if debug:
        logging.info("Task sequence numbers from JSON in show_solved:")
        for _, row in task_df.iterrows():
            logging.info(
                f"Project: {row.get('Project', 'N/A')}, Sequence: {row.get('Sequence', 'N/A')}, Task: {row['Task']}"
            )

    parameters: TimeTableDataParameters = DATA_PARAMS
    start_date = datetime.now().date()
    randomizer = random.Random(parameters.random_seed)
    employees = generate_employees(parameters, randomizer)

    # Generate task IDs
    ids = (str(i) for i in range(len(task_df)))

    # Generate tasks from the DataFrame
    tasks = []
    for _, row in task_df.iterrows():
        tasks.append(
            Task(
                id=next(ids),
                description=row["Task"],
                duration_slots=int(float(row["Duration (hours)"]) * 2),
                start_slot=0,
                required_skill=row["Required Skill"],
                project_id=row.get("Project", ""),
                sequence_number=int(row.get("Sequence", 0)),
            )
        )

    # Generate employee availability preferences
    generate_employee_availability(employees, parameters, start_date, randomizer)
    schedule: EmployeeSchedule = EmployeeSchedule(
        employees=employees,
        tasks=tasks,
        schedule_info=ScheduleInfo(total_slots=parameters.days_in_schedule * 16),
    )

    # Wait for the solver
    emp_df, solved_task_df, new_job_id, status = await solve_schedule(schedule, debug)

    # Return the solved schedule
    return emp_df, solved_task_df, new_job_id, status, task_df_json


async def solve_schedule(
    schedule: EmployeeSchedule, debug: bool = False
) -> Tuple[pd.DataFrame, pd.DataFrame, str, str]:
    """
    Solves the schedule and returns the dataframes and job_id.
    """
    if schedule is None:
        return None, None, None, "No schedule to solve. Please load data first."

    job_id: str = str(uuid.uuid4())

    # Start solving asynchronously
    def listener(solution):
        solved_schedules[job_id] = solution

    solver_manager.solve_and_listen(job_id, schedule, listener)

    emp_df = employees_to_dataframe(schedule)
    task_df = schedule_to_dataframe(schedule)

    task_df = task_df[
        [
            "Project",
            "Sequence",
            "Employee",
            "Task",
            "Start",
            "End",
            "Duration (hours)",
            "Required Skill",
        ]
    ].sort_values(["Project", "Sequence"])

    return emp_df, task_df, job_id, "Solving..."


async def load_data(
    file_obj, llm_output, debug: bool = False
) -> Tuple[pd.DataFrame, pd.DataFrame, gr.update, str, dict]:
    """
    Handle data loading
    Returns (employees_table, schedule_table, job_id_state, status_text, llm_output_state)
    """
    if file_obj is None:
        logging.error(
            "NO FILE OBJECT: User attempted to load data without uploading a file."
        )
        return (
            gr.update(),
            gr.update(),
            gr.update(),
            "No file uploaded. Please upload a file.",
            gr.update(),
        )

    try:
        # Support multiple files. Gradio returns a list when multiple files are selected.
        files = file_obj if isinstance(file_obj, list) else [file_obj]

        combined_tasks: List[Task] = []
        combined_employees: Dict[str, Employee] = {}

        for idx, single_file in enumerate(files):
            # Derive a project ID from the filename (fallback to index)
            try:
                project_id = os.path.splitext(os.path.basename(single_file.name))[0]
            except AttributeError:
                project_id = f"project_{idx+1}"

            schedule_part: EmployeeSchedule = await generate_agent_data(
                single_file, project_id=project_id
            )

            # Merge employees (unique by name)
            for emp in schedule_part.employees:
                if emp.name not in combined_employees:
                    combined_employees[emp.name] = emp

            # Append tasks with project id already set
            combined_tasks.extend(schedule_part.tasks)

        parameters: TimeTableDataParameters = DATA_PARAMS
        final_schedule: EmployeeSchedule = EmployeeSchedule(
            employees=list(combined_employees.values()),
            tasks=combined_tasks,
            schedule_info=ScheduleInfo(total_slots=parameters.days_in_schedule * 16),
        )

        emp_df: pd.DataFrame = employees_to_dataframe(final_schedule)
        task_df: pd.DataFrame = schedule_to_dataframe(final_schedule)

        # Before solving, sort by project and sequence to maintain original order
        # After solving, tasks will be sorted by start time
        task_df: pd.DataFrame = task_df[
            [
                "Project",
                "Sequence",
                "Employee",
                "Task",
                "Start",
                "End",
                "Duration (hours)",
                "Required Skill",
            ]
        ].sort_values(["Project", "Sequence"])

        if debug:
            # Log sequence numbers for debugging
            logging.info("Task sequence numbers after load_data:")
            for _, row in task_df.iterrows():
                logging.info(
                    f"Project: {row['Project']}, Sequence: {row['Sequence']}, Task: {row['Task']}"
                )
            # Log the first few rows of the DataFrame for debugging
            logging.info("Task DataFrame being set in load_data: %s", task_df.head())

        # Store schedule for later use
        job_id = str(uuid.uuid4())
        solved_schedules[job_id] = final_schedule

        # Convert to JSON for state
        task_df_json: str = task_df.to_json(orient="split")

        return (
            emp_df,  # employees_table
            task_df,  # schedule_table
            job_id,  # job_id_state
            "Data loaded successfully",  # status_text
            task_df_json,  # llm_output_state
        )

    except Exception as e:
        logging.error(f"Error loading data: {e}")
        return (
            gr.update(),
            gr.update(),
            gr.update(),
            f"Error loading data: {str(e)}",
            gr.update(),
        )


def start_timer(job_id, llm_output) -> gr.Timer:
    return gr.Timer(active=True)


def poll_solution(
    job_id: str, schedule: EmployeeSchedule, debug: bool = False
) -> Tuple[pd.DataFrame, pd.DataFrame, str, str, object]:
    """
    Poll for a solution for a given job_id.

    Args:
        job_id (str): The job_id to poll for.
        schedule (object): The current schedule state.
        debug (bool): Whether to enable debug logging.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame, str, str, object]: The solved schedule.
    """
    if job_id and job_id in solved_schedules:
        solved_schedule: EmployeeSchedule = solved_schedules[job_id]

        emp_df: pd.DataFrame = employees_to_dataframe(solved_schedule)
        task_df: pd.DataFrame = schedule_to_dataframe(solved_schedule)

        if debug:
            # Log solved task order for debugging
            logging.info("Solved task order:")
            for _, row in task_df.iterrows():
                logging.info(
                    f"Project: {row['Project']}, Sequence: {row['Sequence']}, Task: {row['Task'][:30]}, Start: {row['Start']}"
                )

        task_df: pd.DataFrame = task_df[
            [
                "Project",
                "Sequence",
                "Employee",
                "Task",
                "Start",
                "End",
                "Duration (hours)",
                "Required Skill",
            ]
        ].sort_values(["Start"])

        return emp_df, task_df, job_id, "Solved!", solved_schedule

    return None, None, job_id, "Solving...", schedule


async def auto_poll(
    job_id: str, llm_output: dict, debug: bool = False
) -> Tuple[pd.DataFrame, pd.DataFrame, str, str, dict]:
    """Poll for updates"""
    try:
        if job_id and job_id in solved_schedules:
            schedule = solved_schedules[job_id]
            emp_df = employees_to_dataframe(schedule)
            task_df = schedule_to_dataframe(schedule)

            # Sort tasks by start time for display
            task_df = task_df.sort_values("Start")

            if debug:
                logging.info(f"Polling for job {job_id}")
                logging.info(f"Current schedule state: {task_df.head()}")

            return (
                emp_df,  # employees_table
                task_df,  # schedule_table
                job_id,  # job_id_state
                "Solution updated",  # status_text
                llm_output,  # llm_output_state
            )
    except Exception as e:
        logging.error(f"Error polling: {e}")
        return (
            gr.update(),
            gr.update(),
            job_id,
            f"Error polling: {str(e)}",
            llm_output,
        )

    return (gr.update(), gr.update(), None, "No updates", llm_output)
