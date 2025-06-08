# =========================
#        GENERAL IMPORTS
# =========================
import os, uuid, random
import pandas as pd
from datetime import datetime, timedelta

import logging

logging.basicConfig(level=logging.INFO)

from utils.load_secrets import load_secrets

if not os.getenv("NEBIUS_API_KEY") or not os.getenv("NEBIUS_MODEL"):
    load_secrets("tests/secrets/nebius_secrets.py")

# =========================
#          GRADIO
# =========================
import gradio as gr

# =========================
#     TIMETABLE SOLVER
# =========================
from factory.data_provider import (
    generate_agent_data,
    DATA_PARAMS,
    generate_employees,
    generate_employee_availability,
)

from constraint_solvers.timetable.solver import solver_manager
from constraint_solvers.timetable.domain import EmployeeSchedule, ScheduleInfo, Task

solved_schedules: dict[str, EmployeeSchedule] = {}


# =========================
#           APP
# =========================

DEBUG: bool = False


def app():
    with gr.Blocks() as demo:
        gr.Markdown("# SWE Team Task Scheduling Demo")

        file_upload = gr.File(
            label="Upload Project File (Markdown)",
            file_types=[".md"],
            file_count="single",
            visible=True,
        )

        # State for LLM output, persists per session
        llm_output_state = gr.State(value=None)
        job_id_state = gr.State(value=None)
        status_text = gr.Textbox(label="Solver Status", interactive=False)

        with gr.Row():
            load_btn = gr.Button("Load Data")
            solve_btn = gr.Button("Solve")

        gr.Markdown("## Employees")
        employees_table = gr.Dataframe(label="Employees", interactive=False)

        gr.Markdown("## Tasks")
        schedule_table = gr.Dataframe(label="Tasks Table", interactive=False)

        # Outputs: always keep state as last output
        outputs = [
            employees_table,
            schedule_table,
            job_id_state,
            status_text,
            llm_output_state,
        ]

        # Timer for polling (not related to state)
        timer = gr.Timer(2, active=False)
        timer.tick(auto_poll, inputs=[job_id_state, llm_output_state], outputs=outputs)

        # Use state as both input and output
        load_btn.click(
            load_data,
            inputs=[file_upload, llm_output_state],
            outputs=outputs,
            api_name="load_data",
        )

        solve_btn.click(
            show_solved, inputs=[llm_output_state, job_id_state], outputs=outputs
        ).then(start_timer, inputs=[job_id_state, llm_output_state], outputs=timer)

        if DEBUG:

            def debug_set_state(state):
                logging.info(f"DEBUG: Setting state to test_value")
                return "Debug: State set!", "test_value"

            def debug_show_state(state):
                logging.info(f"DEBUG: Current state is {state}")
                return f"Debug: Current state: {state}", gr.update()

            debug_out = gr.Textbox(label="Debug Output")
            debug_set_btn = gr.Button("Debug Set State")
            debug_show_btn = gr.Button("Debug Show State")

            debug_set_btn.click(
                debug_set_state,
                inputs=[llm_output_state],
                outputs=[debug_out, llm_output_state],
            )
            debug_show_btn.click(
                debug_show_state,
                inputs=[llm_output_state],
                outputs=[debug_out, gr.State()],
            )

    return demo


# =========================
#      EVENT FUNCTIONS
# =========================
async def show_solved(
    task_df_json, job_id
) -> tuple[pd.DataFrame, pd.DataFrame, str, str, object]:
    logging.info("Task DataFrame JSON received in show_solved: %s", task_df_json)
    if not task_df_json:
        return (
            gr.update(),
            gr.update(),
            None,
            "No schedule to solve. Please load data first.",
            None,
        )
    import pandas as pd
    from io import StringIO

    task_df: pd.DataFrame = pd.read_json(StringIO(task_df_json), orient="split")
    parameters: TimeTableDataParameters = DATA_PARAMS
    start_date: datetime = datetime.now().date()
    randomizer: random.Random = random.Random(parameters.random_seed)
    employees = generate_employees(parameters, randomizer)

    # Generate task IDs
    ids = (str(i) for i in range(len(task_df)))

    # Generate tasks from the DataFrame
    tasks = [
        Task(
            id=next(ids),
            description=row["Task"],
            # Convert hours back to slots
            duration_slots=int(float(row["Duration (hours)"]) * 2),
            start_slot=0,
            required_skill=row["Required Skill"],
        )
        for _, row in task_df.iterrows()
    ]

    # Generate employee availability preferences
    #
    generate_employee_availability(employees, parameters, start_date, randomizer)
    schedule: EmployeeSchedule = EmployeeSchedule(
        employees=employees,
        tasks=tasks,
        schedule_info=ScheduleInfo(total_slots=parameters.days_in_schedule * 16),
    )

    # Wait for the solver
    emp_df, solved_task_df, new_job_id, status = await solve_schedule(schedule)

    # Return the solved schedule
    return emp_df, solved_task_df, new_job_id, status, task_df_json


async def solve_schedule(schedule) -> tuple[pd.DataFrame, pd.DataFrame, str, str]:
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
        ["Employee", "Task", "Start", "End", "Duration (hours)", "Required Skill"]
    ].sort_values(["Employee", "Start"])

    return emp_df, task_df, job_id, "Solving..."


async def load_data(file_obj, llm_output):
    if file_obj is None:
        logging.error(
            "NO FILE OBJECT: User attempted to load data without uploading a file."
        )

        # Show an error message in the status_text output, too
        return (
            gr.update(),
            gr.update(),
            gr.update(),
            "No file uploaded. Please upload a file.",
            gr.update(),
        )

    schedule = await generate_agent_data(file_obj)

    emp_df: pd.DataFrame = employees_to_dataframe(schedule)
    task_df: pd.DataFrame = schedule_to_dataframe(schedule)

    # Sort the tasks by employee and start time
    # TODO: should have task dependency constraints, but we don't have that yet
    task_df: pd.DataFrame = task_df[
        ["Employee", "Task", "Start", "End", "Duration (hours)", "Required Skill"]
    ].sort_values(["Employee", "Start"])

    # Convert to JSON
    task_df_json: str = task_df.to_json(orient="split")

    if DEBUG:
        # Log the first few rows of the DataFrame for debugging
        logging.info("Task DataFrame being set in load_data: %s", task_df.head())

    # Always set the state to the new DataFrame JSON when new data is loaded
    return emp_df, task_df, gr.update(), gr.update(), task_df_json


def start_timer(job_id, llm_output) -> gr.Timer:
    return gr.Timer(active=True)


def poll_solution(
    job_id, schedule
) -> tuple[pd.DataFrame, pd.DataFrame, str, str, object]:
    """
    Poll for a solution for a given job_id.

    Args:
        job_id (str): The job_id to poll for.
        schedule (object): The current schedule state.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame, str, str, object]: The solved schedule.
    """
    if job_id and job_id in solved_schedules:
        solved_schedule: EmployeeSchedule = solved_schedules[job_id]

        emp_df: pd.DataFrame = employees_to_dataframe(solved_schedule)
        task_df: pd.DataFrame = schedule_to_dataframe(solved_schedule)

        task_df: pd.DataFrame = task_df[
            ["Employee", "Task", "Start", "End", "Duration (hours)", "Required Skill"]
        ].sort_values(["Employee", "Start"])

        return emp_df, task_df, job_id, "Solved!", solved_schedule

    return None, None, job_id, "Solving...", schedule


def auto_poll(
    job_id: str, schedule
) -> tuple[pd.DataFrame, pd.DataFrame, str, str, object]:
    """
    Poll for a solution for a given job_id.

    Args:
        job_id (str): The job_id to poll for.
        schedule (object): The current schedule state.
    """
    if job_id:
        emp_df, task_df, job_id, status, schedule = poll_solution(job_id, schedule)
        return emp_df, task_df, job_id, status, schedule

    # Defensive: always return 5 values, even if all are None
    return (
        gr.update(),  # employees_table
        gr.update(),  # schedule_table
        None,  # job_id_state
        gr.update(),  # status_text
        None,  # schedule_state
    )


# =========================
#     HELPER FUNCTIONS
# =========================
def schedule_to_dataframe(schedule) -> pd.DataFrame:
    """
    Convert an EmployeeSchedule to a pandas DataFrame.

    Args:
        schedule (EmployeeSchedule): The schedule to convert.

    Returns:
        pd.DataFrame: The converted DataFrame.
    """
    data: list[dict[str, str]] = []

    # Process each task in the schedule
    for task in schedule.tasks:
        # Get employee name or "Unassigned" if no employee assigned
        employee: str = task.employee.name if task.employee else "Unassigned"

        # Calculate start and end times based on 30-minute slots
        start_time: datetime = datetime.now() + timedelta(minutes=30 * task.start_slot)
        end_time: datetime = start_time + timedelta(minutes=30 * task.duration_slots)

        # Add task data to list with availability flags
        data.append(
            {
                "Employee": employee,
                "Task": task.description,
                "Start": start_time,
                "End": end_time,
                "Duration (hours)": task.duration_slots / 2,  # Convert slots to hours
                "Required Skill": task.required_skill,
                # Check if task falls on employee's unavailable date
                "Unavailable": employee != "Unassigned"
                and hasattr(task.employee, "unavailable_dates")
                and start_time.date() in task.employee.unavailable_dates,
                # Check if task falls on employee's undesired date
                "Undesired": employee != "Unassigned"
                and hasattr(task.employee, "undesired_dates")
                and start_time.date() in task.employee.undesired_dates,
                # Check if task falls on employee's desired date
                "Desired": employee != "Unassigned"
                and hasattr(task.employee, "desired_dates")
                and start_time.date() in task.employee.desired_dates,
            }
        )

    return pd.DataFrame(data)


def employees_to_dataframe(schedule) -> pd.DataFrame:
    """
    Convert an EmployeeSchedule to a pandas DataFrame.

    Args:
        schedule (EmployeeSchedule): The schedule to convert.
    """
    data: list[dict[str, str]] = []

    for emp in schedule.employees:
        first, last = emp.name.split(" ", 1) if " " in emp.name else (emp.name, "")
        data.append(
            {
                "First Name": first,
                "Last Name": last,
                "Skills": ", ".join(sorted(emp.skills)),
            }
        )

    return pd.DataFrame(data)


if __name__ == "__main__":
    app().launch()
