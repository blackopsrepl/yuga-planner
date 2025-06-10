import os, random, uuid, logging
from io import StringIO
from datetime import datetime
import threading
import time

from typing import Tuple, Dict, List, Optional

import pandas as pd

import gradio as gr
from state import app_state

from constraint_solvers.timetable.solver import solver_manager
from domain import MOCK_PROJECTS

from helpers import schedule_to_dataframe, employees_to_dataframe

from factory.data_provider import (
    generate_agent_data,
    DATA_PARAMS,
    TimeTableDataParameters,
    generate_employees,
    generate_employee_availability,
    SLOTS_PER_DAY,
)

from constraint_solvers.timetable.domain import (
    EmployeeSchedule,
    ScheduleInfo,
    Task,
    Employee,
)


class LogCapture:
    """Helper class to capture logs for streaming to UI"""

    def __init__(self):
        self.logs = []
        self.lock = threading.Lock()

    def add_log(self, message):
        with self.lock:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.logs.append(f"[{timestamp}] {message}")

    def get_logs(self):
        with self.lock:
            return "\n".join(self.logs)

    def clear(self):
        with self.lock:
            self.logs.clear()


class StreamingLogHandler(logging.Handler):
    """Custom log handler that captures logs for UI streaming"""

    def __init__(self, log_capture):
        super().__init__()
        self.log_capture = log_capture

    def emit(self, record):
        try:
            msg = self.format(record)
            self.log_capture.add_log(msg)
        except Exception:
            self.handleError(record)


# Global log capture instance for streaming
log_capture = LogCapture()


def setup_log_streaming():
    """Set up log streaming to capture logs for UI"""
    logger = logging.getLogger()
    # Remove existing handlers to avoid duplicate logs
    for handler in logger.handlers[:]:
        if isinstance(handler, StreamingLogHandler):
            logger.removeHandler(handler)

    # Add our streaming handler
    stream_handler = StreamingLogHandler(log_capture)
    stream_handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(levelname)s - %(message)s")
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)


def get_streaming_logs():
    """Get accumulated logs for streaming to UI"""
    return log_capture.get_logs()


def clear_streaming_logs():
    """Clear accumulated logs"""
    log_capture.clear()


async def show_solved(
    state_data, job_id: str, debug: bool = False
) -> Tuple[pd.DataFrame, pd.DataFrame, str, str, object, str]:
    # Set up log streaming for solving process
    setup_log_streaming()

    # Add debugging to understand what's happening
    logging.info(
        f"🔧 show_solved called with state_data type: {type(state_data)}, job_id: {job_id}"
    )
    logging.info("🚀 Starting solve process...")

    # Handle both old format (string) and new format (dict) for backward compatibility
    if isinstance(state_data, str):
        task_df_json = state_data
        employee_count = None
        days_in_schedule = None
    elif isinstance(state_data, dict):
        task_df_json = state_data.get("task_df_json")
        employee_count = state_data.get("employee_count")
        days_in_schedule = state_data.get("days_in_schedule")
    else:
        task_df_json = None
        employee_count = None
        days_in_schedule = None

    # Dataframe from JSON debug logging
    if debug:
        logging.info("Task DataFrame JSON received in show_solved: %s", task_df_json)

    if not task_df_json:
        logging.warning("❌ No task_df_json provided to show_solved")
        return (
            gr.update(),
            gr.update(),
            None,
            "No schedule to solve. Please load data first using the 'Load Data' button.",
            None,
            get_streaming_logs(),  # log_terminal
        )

    try:
        logging.info("📋 Parsing task data from JSON...")
        task_df: pd.DataFrame = pd.read_json(StringIO(task_df_json), orient="split")
        logging.info(f"📊 Found {len(task_df)} tasks to schedule")
    except Exception as e:
        logging.error(f"❌ Error parsing task_df_json: {e}")
        return (
            gr.update(),
            gr.update(),
            None,
            f"Error parsing task data: {str(e)}",
            None,
            get_streaming_logs(),  # log_terminal
        )

    # Log sequence numbers from JSON for debugging
    if debug:
        logging.info("Task sequence numbers from JSON in show_solved:")
        for _, row in task_df.iterrows():
            logging.info(
                f"Project: {row.get('Project', 'N/A')}, Sequence: {row.get('Sequence', 'N/A')}, Task: {row['Task']}"
            )

    parameters: TimeTableDataParameters = DATA_PARAMS

    # Override parameters if provided from UI
    if employee_count is not None or days_in_schedule is not None:
        parameters = TimeTableDataParameters(
            skill_set=parameters.skill_set,
            days_in_schedule=days_in_schedule
            if days_in_schedule is not None
            else parameters.days_in_schedule,
            employee_count=employee_count
            if employee_count is not None
            else parameters.employee_count,
            optional_skill_distribution=parameters.optional_skill_distribution,
            availability_count_distribution=parameters.availability_count_distribution,
            random_seed=parameters.random_seed,
        )

    logging.info("👥 Generating employees and availability...")
    start_date = datetime.now().date()
    randomizer = random.Random(parameters.random_seed)
    employees = generate_employees(parameters, randomizer)
    logging.info(f"✅ Generated {len(employees)} employees")

    # Generate task IDs
    logging.info("🆔 Generating task IDs and converting to solver format...")
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
    logging.info(f"✅ Converted {len(tasks)} tasks for solver")

    # Generate employee availability preferences
    logging.info("📅 Generating employee availability preferences...")
    generate_employee_availability(employees, parameters, start_date, randomizer)
    logging.info("✅ Employee availability generated")
    schedule: EmployeeSchedule = EmployeeSchedule(
        employees=employees,
        tasks=tasks,
        schedule_info=ScheduleInfo(
            total_slots=parameters.days_in_schedule * SLOTS_PER_DAY
        ),
    )

    try:
        logging.info("🔍 Starting constraint solver...")
        # Wait for the solver
        emp_df, solved_task_df, new_job_id, status = await solve_schedule(
            schedule, debug
        )
        logging.info("📈 Solver process initiated successfully")

        # Return the solved schedule
        return (
            emp_df,
            solved_task_df,
            new_job_id,
            status,
            state_data,
            get_streaming_logs(),
        )  # log_terminal
    except Exception as e:
        logging.error(f"Error in solve_schedule: {e}")
        return (
            gr.update(),
            gr.update(),
            None,
            f"Error solving schedule: {str(e)}",
            state_data,
            gr.update(),  # log_terminal
        )


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
        app_state.add_solved_schedule(job_id, solution)

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


def show_mock_project_content(project_names) -> str:
    """
    Display the content of selected mock projects.
    """
    if not project_names:
        return "No projects selected."

    # Handle both single string and list of strings
    if isinstance(project_names, str):
        project_names = [project_names]

    content_parts = []
    for project_name in project_names:
        if project_name in MOCK_PROJECTS:
            content_parts.append(
                f"=== {project_name.upper()} ===\n\n{MOCK_PROJECTS[project_name]}"
            )
        else:
            content_parts.append(
                f"=== {project_name.upper()} ===\n\nProject not found."
            )

    return (
        "\n\n" + "=" * 50 + "\n\n".join(content_parts)
        if content_parts
        else "No valid projects selected."
    )


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
    Handle data loading from either file uploads or mock projects - streaming version
    Yields intermediate updates for real-time progress
    """
    # Set up log streaming and clear previous logs
    setup_log_streaming()
    clear_streaming_logs()

    # Initial log message
    logging.info("🚀 Starting data loading process...")

    # Yield initial state
    yield (
        gr.update(),  # employees_table
        gr.update(),  # schedule_table
        gr.update(),  # job_id_state
        "Starting data loading...",  # status_text
        gr.update(),  # llm_output_state
        get_streaming_logs(),  # log_terminal
    )

    try:
        if project_source == "Upload Project Files":
            # Handle file upload option
            logging.info("📁 Processing uploaded files...")
            if file_obj is None:
                logging.error(
                    "❌ NO FILE OBJECT: User attempted to load data without uploading a file."
                )
                yield (
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    "No file uploaded. Please upload a file.",
                    gr.update(),
                    get_streaming_logs(),  # log_terminal
                )
                return

            # Support multiple files. Gradio returns a list when multiple files are selected.
            files = file_obj if isinstance(file_obj, list) else [file_obj]
            project_source_info = f"{len(files)} file(s)"
            logging.info(f"📄 Found {len(files)} file(s) to process")
        else:
            # Handle mock project option
            logging.info("🎭 Processing mock projects...")
            if not mock_projects:
                logging.error(
                    "❌ INVALID MOCK PROJECT: User didn't select any mock projects"
                )
                yield (
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    "Please select at least one mock project.",
                    gr.update(),
                    get_streaming_logs(),  # log_terminal
                )
                return

            # Ensure mock_projects is a list
            if isinstance(mock_projects, str):
                mock_projects = [mock_projects]

            # Validate all selected mock projects
            invalid_projects = [p for p in mock_projects if p not in MOCK_PROJECTS]
            if invalid_projects:
                logging.error(f"INVALID MOCK PROJECTS: {invalid_projects}")
                yield (
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    f"Invalid mock projects selected: {', '.join(invalid_projects)}",
                    gr.update(),
                    get_streaming_logs(),  # log_terminal
                )
                return

            # Create file content list from selected mock projects
            files = [MOCK_PROJECTS[project] for project in mock_projects]
            project_source_info = (
                f"{len(mock_projects)} mock project(s): {', '.join(mock_projects)}"
            )
            logging.info(f"📋 Selected mock projects: {', '.join(mock_projects)}")

        # Yield progress update after validation
        yield (
            gr.update(),  # employees_table
            gr.update(),  # schedule_table
            gr.update(),  # job_id_state
            f"Processing {len(files)} project(s)...",  # status_text
            gr.update(),  # llm_output_state
            get_streaming_logs(),  # log_terminal
        )

        combined_tasks: List[Task] = []
        combined_employees: Dict[str, Employee] = {}

        logging.info(f"🔄 Processing {len(files)} project(s)...")

        # Process each file with real-time progress updates
        for idx, single_file in enumerate(files):
            # Derive a project ID from the filename (fallback to index)
            if project_source == "Upload Project Files":
                try:
                    project_id = os.path.splitext(os.path.basename(single_file.name))[0]
                except AttributeError:
                    project_id = f"project_{idx+1}"
            else:
                # For mock projects, use the mock project name as the project ID
                project_id = mock_projects[idx]

            logging.info(f"⚙️ Processing project {idx+1}/{len(files)}: '{project_id}'")

            # Yield progress update for each project start
            yield (
                gr.update(),  # employees_table
                gr.update(),  # schedule_table
                gr.update(),  # job_id_state
                f"Processing project {idx+1}/{len(files)}: {project_id}",  # status_text
                gr.update(),  # llm_output_state
                get_streaming_logs(),  # log_terminal
            )

            schedule_part: EmployeeSchedule = await generate_agent_data(
                single_file,
                project_id=project_id,
                employee_count=employee_count,
                days_in_schedule=days_in_schedule,
            )
            logging.info(f"✅ Completed processing project '{project_id}'")

            # Merge employees (unique by name)
            for emp in schedule_part.employees:
                if emp.name not in combined_employees:
                    combined_employees[emp.name] = emp

            # Append tasks with project id already set
            combined_tasks.extend(schedule_part.tasks)

            # Yield progress update for each project completion
            yield (
                gr.update(),  # employees_table
                gr.update(),  # schedule_table
                gr.update(),  # job_id_state
                f"Completed {idx+1}/{len(files)} projects",  # status_text
                gr.update(),  # llm_output_state
                get_streaming_logs(),  # log_terminal
            )

        logging.info(
            f"👥 Merging data: {len(combined_employees)} unique employees, {len(combined_tasks)} total tasks"
        )

        # Yield progress update for final processing
        yield (
            gr.update(),  # employees_table
            gr.update(),  # schedule_table
            gr.update(),  # job_id_state
            "Building final schedule...",  # status_text
            gr.update(),  # llm_output_state
            get_streaming_logs(),  # log_terminal
        )

        parameters: TimeTableDataParameters = DATA_PARAMS

        # Override with custom parameters if provided
        if employee_count is not None or days_in_schedule is not None:
            logging.info(
                f"⚙️ Customizing parameters: {employee_count} employees, {days_in_schedule} days"
            )
            parameters = TimeTableDataParameters(
                skill_set=parameters.skill_set,
                days_in_schedule=days_in_schedule
                if days_in_schedule is not None
                else parameters.days_in_schedule,
                employee_count=employee_count
                if employee_count is not None
                else parameters.employee_count,
                optional_skill_distribution=parameters.optional_skill_distribution,
                availability_count_distribution=parameters.availability_count_distribution,
                random_seed=parameters.random_seed,
            )

        logging.info("🏗️ Building final schedule structure...")
        final_schedule: EmployeeSchedule = EmployeeSchedule(
            employees=list(combined_employees.values()),
            tasks=combined_tasks,
            schedule_info=ScheduleInfo(
                total_slots=parameters.days_in_schedule * SLOTS_PER_DAY
            ),
        )

        logging.info("📊 Converting to data tables...")
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
        app_state.add_solved_schedule(job_id, final_schedule)

        logging.info("💾 Storing schedule state...")
        # Convert to JSON for state and include parameters
        state_data = {
            "task_df_json": task_df.to_json(orient="split"),
            "employee_count": employee_count,
            "days_in_schedule": days_in_schedule,
        }

        logging.info("🎉 Data loading completed successfully!")

        # Final yield with complete results
        yield (
            emp_df,  # employees_table
            task_df,  # schedule_table
            job_id,  # job_id_state
            f"Data loaded successfully from {project_source_info}",  # status_text
            state_data,  # llm_output_state
            get_streaming_logs(),  # log_terminal with accumulated logs
        )

    except Exception as e:
        logging.error(f"Error loading data: {e}")
        yield (
            gr.update(),
            gr.update(),
            gr.update(),
            f"Error loading data: {str(e)}",
            gr.update(),
            get_streaming_logs(),  # log_terminal
        )


def start_timer(job_id, llm_output) -> gr.Timer:
    return gr.Timer(active=True)


def analyze_constraint_violations(solved_schedule: EmployeeSchedule) -> str:
    """
    Analyze a solved schedule to identify specific constraint violations.

    This function examines a solved schedule to determine why hard constraints
    were violated, helping users understand what makes their scheduling problem
    infeasible.

    Common reasons for infeasibility:
    1. Not enough employees with required skills
    2. Tasks require more time than available in the schedule window
    3. Employee availability constraints conflict with task requirements
    4. Tasks within a project cannot be sequenced due to time conflicts
    5. Total task duration exceeds available employee time

    Args:
        solved_schedule: The solved EmployeeSchedule with potential violations

    Returns:
        str: Detailed description of constraint violations with actionable suggestions
    """
    violations = []

    # Check for unassigned tasks (tasks without employees)
    unassigned_tasks = [task for task in solved_schedule.tasks if task.employee is None]
    if unassigned_tasks:
        violations.append(
            f"• {len(unassigned_tasks)} tasks could not be assigned to any employee"
        )
        # Show which skills are missing
        required_skills = set(task.required_skill for task in unassigned_tasks)
        available_skills = set()
        for emp in solved_schedule.employees:
            available_skills.update(emp.skills)
        missing_skills = required_skills - available_skills
        if missing_skills:
            violations.append(f"  - Missing skills: {', '.join(missing_skills)}")

    # Check for skill mismatches
    skill_violations = [
        task
        for task in solved_schedule.tasks
        if task.employee is not None and task.required_skill not in task.employee.skills
    ]
    if skill_violations:
        violations.append(
            f"• {len(skill_violations)} tasks assigned to employees without required skills"
        )

    # Check for tasks scheduled outside the time window
    invalid_time_tasks = [
        task
        for task in solved_schedule.tasks
        if task.start_slot < 0
        or (task.start_slot + task.duration_slots)
        > solved_schedule.schedule_info.total_slots
    ]
    if invalid_time_tasks:
        violations.append(
            f"• {len(invalid_time_tasks)} tasks scheduled outside the available time window"
        )
        total_task_hours = (
            sum(task.duration_slots for task in solved_schedule.tasks) * 0.5
        )
        total_available_hours = (
            solved_schedule.schedule_info.total_slots
            * len(solved_schedule.employees)
            * 0.5
        )
        violations.append(f"  - Total task time needed: {total_task_hours:.1f} hours")
        violations.append(
            f"  - Total available time: {total_available_hours:.1f} hours"
        )

    # Check for overlapping tasks for the same employee
    overlapping_tasks = []
    employee_tasks = {}
    for task in solved_schedule.tasks:
        if task.employee is not None:
            if task.employee.name not in employee_tasks:
                employee_tasks[task.employee.name] = []
            employee_tasks[task.employee.name].append(task)

    for employee_name, tasks in employee_tasks.items():
        for i, task1 in enumerate(tasks):
            for task2 in tasks[i + 1 :]:
                if (
                    task1.start_slot < task2.start_slot + task2.duration_slots
                    and task2.start_slot < task1.start_slot + task1.duration_slots
                ):
                    overlapping_tasks.append((task1, task2))

    if overlapping_tasks:
        violations.append(
            f"• {len(overlapping_tasks)} pairs of tasks overlap for the same employee"
        )

    # Check for tasks scheduled during employee unavailable dates
    from constraint_solvers.timetable.constraints import get_slot_date

    unavailable_violations = [
        task
        for task in solved_schedule.tasks
        if task.employee is not None
        and get_slot_date(task.start_slot) in task.employee.unavailable_dates
    ]
    if unavailable_violations:
        violations.append(
            f"• {len(unavailable_violations)} tasks scheduled when employees are unavailable"
        )

    if violations:
        return "Specific constraint violations:\n" + "\n".join(violations)
    else:
        return "No specific violations detected (solver may have other internal constraints)."


def poll_solution(
    job_id: str, schedule: EmployeeSchedule, debug: bool = False
) -> Tuple[pd.DataFrame, pd.DataFrame, str, str, object, str]:
    """
    Poll for a solution for a given job_id.

    Args:
        job_id (str): The job_id to poll for.
        schedule (object): The current schedule state.
        debug (bool): Whether to enable debug logging.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame, str, str, object]: The solved schedule.
    """
    if job_id and app_state.has_solved_schedule(job_id):
        solved_schedule: EmployeeSchedule = app_state.get_solved_schedule(job_id)

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

        # Check if hard constraints are violated (infeasible solution)
        status_message = "Solved!"
        if solved_schedule.score is not None:
            hard_score = solved_schedule.score.hard_score
            if hard_score < 0:
                # Hard constraints are violated - the problem is infeasible
                violation_count = abs(int(hard_score))
                violation_details = analyze_constraint_violations(solved_schedule)
                status_message = f"⚠️ CONSTRAINTS VIOLATED: {violation_count} hard constraint(s) could not be satisfied. The schedule is not feasible.\n\n{violation_details}\n\nSuggestions:\n• Add more employees with required skills\n• Increase the scheduling time window\n• Reduce task requirements or durations\n• Check employee availability constraints"
                logging.warning(
                    f"Infeasible solution detected. Hard score: {hard_score}"
                )
            else:
                soft_score = solved_schedule.score.soft_score
                status_message = f"✅ Solved successfully! Score: {hard_score}/{soft_score} (hard/soft)"
                logging.info(
                    f"Feasible solution found. Score: {hard_score}/{soft_score}"
                )

        return (
            emp_df,
            task_df,
            job_id,
            status_message,
            solved_schedule,
            gr.update(),
        )  # log_terminal

    return None, None, job_id, "Solving...", schedule, gr.update()  # log_terminal


async def auto_poll(
    job_id: str, llm_output: dict, debug: bool = False
) -> Tuple[pd.DataFrame, pd.DataFrame, str, str, dict, str]:
    """Poll for updates"""
    try:
        if job_id and app_state.has_solved_schedule(job_id):
            schedule = app_state.get_solved_schedule(job_id)
            emp_df = employees_to_dataframe(schedule)
            task_df = schedule_to_dataframe(schedule)

            # Sort tasks by start time for display
            task_df = task_df.sort_values("Start")

            if debug:
                logging.info(f"Polling for job {job_id}")
                logging.info(f"Current schedule state: {task_df.head()}")

            # Check if hard constraints are violated (infeasible solution)
            status_message = "Solution updated"
            if schedule.score is not None:
                hard_score = schedule.score.hard_score
                if hard_score < 0:
                    # Hard constraints are violated - the problem is infeasible
                    violation_count = abs(int(hard_score))
                    violation_details = analyze_constraint_violations(schedule)
                    status_message = f"⚠️ CONSTRAINTS VIOLATED: {violation_count} hard constraint(s) could not be satisfied. The schedule is not feasible.\n\n{violation_details}\n\nSuggestions:\n• Add more employees with required skills\n• Increase the scheduling time window\n• Reduce task requirements or durations\n• Check employee availability constraints"
                    logging.warning(
                        f"Infeasible solution detected. Hard score: {hard_score}"
                    )
                else:
                    soft_score = schedule.score.soft_score
                    status_message = f"✅ Solved successfully! Score: {hard_score}/{soft_score} (hard/soft)"
                    logging.info(
                        f"Feasible solution found. Score: {hard_score}/{soft_score}"
                    )

            return (
                emp_df,  # employees_table
                task_df,  # schedule_table
                job_id,  # job_id_state
                status_message,  # status_text
                llm_output,  # llm_output_state
                get_streaming_logs(),  # log_terminal
            )
    except Exception as e:
        logging.error(f"Error polling: {e}")
        return (
            gr.update(),
            gr.update(),
            job_id,
            f"Error polling: {str(e)}",
            llm_output,
            get_streaming_logs(),  # log_terminal
        )

    return (
        gr.update(),
        gr.update(),
        None,
        "No updates",
        llm_output,
        get_streaming_logs(),  # log_terminal
    )


"""
CONSTRAINT VIOLATION DETECTION SYSTEM

This module implements automatic detection of infeasible scheduling problems.
When the Timefold solver cannot satisfy all hard constraints, it returns a
solution with a negative hard score. This system analyzes such solutions to
provide users with specific, actionable feedback about why their scheduling
problem cannot be solved.

HOW IT WORKS:
1. After solving, check if solution.score.hard_score() < 0
2. If negative, analyze the solution to identify specific violations
3. Provide detailed feedback and suggestions to the user

EXAMPLE SCENARIOS WHERE CONSTRAINTS ARE VIOLATED:

Scenario 1 - Missing Skills:
- Task requires "AI Engineer" skill
- No employees have this skill
- Result: Task cannot be assigned → infeasible

Scenario 2 - Insufficient Time:
- 10 tasks requiring 8 hours each (80 hours total)
- 5 employees working 2 days (80 slots = 40 hours total)
- Result: Not enough time to complete all tasks → infeasible

Scenario 3 - Availability Conflicts:
- Critical task must be done by specific employee
- Employee is unavailable during the entire schedule period
- Result: Task cannot be scheduled → infeasible

Scenario 4 - Project Sequencing Impossible:
- Project has Task A → Task B → Task C sequence
- Time window too short to complete sequence
- Result: Sequence constraints cannot be satisfied → infeasible

USER FEEDBACK:
When constraints are violated, users see:
- ⚠️ Warning that constraints are violated
- Specific count of violations
- Detailed breakdown of what went wrong
- Actionable suggestions for fixing the problem

This helps users understand exactly what needs to be changed to make
their scheduling problem solvable.
"""
