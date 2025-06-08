# =========================
#        GENERAL IMPORTS
# =========================
import pandas as pd
import uuid
from datetime import datetime, timedelta

# =========================
#          GRADIO
# =========================
import gradio as gr

# =========================
#     TIMETABLE SOLVER
# =========================
from factory.data_provider import generate_demo_data
from constraint_solvers.timetable.solver import solver_manager

solved_schedules = {}


# =========================
#           APP
# =========================
def app():
    with gr.Blocks() as demo:
        ### HEADER AND STATUS ###
        gr.Markdown("# SWE Team Task Scheduling Demo")

        job_id_state = gr.State(value=None)
        status_text = gr.Textbox(label="Solver Status", interactive=False)

        with gr.Row():
            solve_btn = gr.Button("Solve")

        ### TABLES ###
        gr.Markdown("## Employees")
        employees_table = gr.Dataframe(label="Employees", interactive=False)

        gr.Markdown("## Tasks")
        schedule_table = gr.Dataframe(label="Tasks Table", interactive=False)

        solve_btn.click(
            show_solved,
            inputs=[],
            outputs=[employees_table, schedule_table, job_id_state, status_text],
        )

        demo.load(
            generate_df,
            inputs=[],
            outputs=[employees_table, schedule_table, job_id_state, status_text],
        )

        timer = gr.Timer(2)
        timer.tick(
            auto_poll,
            inputs=job_id_state,
            outputs=[employees_table, schedule_table, job_id_state, status_text],
        )

    return demo


# =========================
#      EVENT FUNCTIONS
# =========================
def show_solved() -> tuple[pd.DataFrame, pd.DataFrame, str, str]:
    emp_df, task_df, job_id, status = solve_schedule()
    return emp_df, task_df, job_id, status


def auto_poll(job_id: str) -> tuple[pd.DataFrame, pd.DataFrame, str, str]:
    if job_id:
        return poll_solution(job_id)

    # Do not clear tables; just leave them as is
    return (
        gr.update(),  # employees_table
        gr.update(),  # schedule_table
        job_id,  # job_id_state
        gr.update(),  # status_text
    )


# =================
#   DATA GENERATION
# =================
def generate_df() -> tuple[pd.DataFrame, pd.DataFrame, None, None]:
    schedule = generate_demo_data()
    emp_df = employees_to_dataframe(schedule)
    task_df = schedule_to_dataframe(schedule)
    task_df = task_df[
        ["Employee", "Task", "Start", "End", "Duration (hours)", "Required Skill"]
    ].sort_values(["Employee", "Start"])
    return emp_df, task_df, None, None


def solve_schedule() -> tuple[pd.DataFrame, pd.DataFrame, str, str]:
    """
    Solves the schedule and returns the dataframes and job_id.
    """
    schedule = generate_demo_data()
    job_id = str(uuid.uuid4())

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


def poll_solution(job_id) -> tuple[pd.DataFrame, pd.DataFrame, str, str]:
    """
    Poll for a solution for a given job_id.

    Args:
        job_id (str): The job_id to poll for.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame, str, str]: The solved schedule.
    """
    if job_id and job_id in solved_schedules:
        solved_schedule = solved_schedules[job_id]

        emp_df = employees_to_dataframe(solved_schedule)
        task_df = schedule_to_dataframe(solved_schedule)

        task_df = task_df[
            ["Employee", "Task", "Start", "End", "Duration (hours)", "Required Skill"]
        ].sort_values(["Employee", "Start"])

        return emp_df, task_df, job_id, "Solved!"

    return None, None, job_id, "Solving..."


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
    data = []
    for task in schedule.tasks:
        employee = task.employee.name if task.employee else "Unassigned"
        start_time = datetime.now() + timedelta(minutes=30 * task.start_slot)
        end_time = start_time + timedelta(minutes=30 * task.duration_slots)
        data.append(
            {
                "Employee": employee,
                "Task": task.description,
                "Start": start_time,
                "End": end_time,
                "Duration (hours)": task.duration_slots / 2,  # Convert slots to hours
                "Required Skill": task.required_skill,
                "Unavailable": employee != "Unassigned"
                and hasattr(task.employee, "unavailable_dates")
                and start_time.date() in task.employee.unavailable_dates,
                "Undesired": employee != "Unassigned"
                and hasattr(task.employee, "undesired_dates")
                and start_time.date() in task.employee.undesired_dates,
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
    data = []
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
