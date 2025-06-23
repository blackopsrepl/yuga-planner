import os, uuid, random
from datetime import datetime, date, timezone
from typing import Tuple, Dict, Any, Optional

import pandas as pd
import gradio as gr

from .state import StateService
from constraint_solvers.timetable.solver import solver_manager

from factory.data.provider import (
    DATA_PARAMS,
    TimeTableDataParameters,
)
from constraint_solvers.timetable.working_hours import SLOTS_PER_WORKING_DAY

from factory.data.generators import (
    generate_employees,
    generate_employee_availability,
)

from factory.data.formatters import schedule_to_dataframe, employees_to_dataframe

from constraint_solvers.timetable.domain import EmployeeSchedule, ScheduleInfo

from .data import DataService
from .constraint_analyzer import ConstraintAnalyzerService

from utils.logging_config import setup_logging, get_logger

# Initialize logging
setup_logging()
logger = get_logger(__name__)


class ScheduleService:
    """Service for handling schedule solving and management operations"""

    @staticmethod
    async def solve_schedule_from_state(
        state_data: Dict[str, Any], job_id: str, debug: bool = False
    ) -> Tuple[pd.DataFrame, pd.DataFrame, str, str, Dict[str, Any]]:
        """
        Solve a schedule from state data.

        Args:
            state_data: State data containing task information and parameters
            job_id: Job identifier for tracking
            debug: Enable debug logging

        Returns:
            Tuple of (emp_df, task_df, new_job_id, status_message, state_data)
        """
        logger.info(f"🔧 solve_schedule_from_state called with job_id: {job_id}")
        logger.info("🚀 Starting solve process...")

        if debug:
            os.environ["YUGA_DEBUG"] = "true"
            # Reconfigure logging for debug mode
            setup_logging("DEBUG")

        else:
            os.environ["YUGA_DEBUG"] = "false"

        # Extract parameters from state data dict
        task_df_json = state_data.get("task_df_json")
        employee_count = state_data.get("employee_count")
        days_in_schedule = state_data.get("days_in_schedule")

        if not task_df_json:
            logger.warning("❌ No task_df_json provided to solve_schedule_from_state")

            return (
                gr.update(),
                gr.update(),
                None,
                "No schedule to solve. Please load data first using the 'Load Data' button.",
                None,
            )

        try:
            # Parse task data
            task_df = DataService.parse_task_data_from_json(task_df_json, debug)

            # Extract base_date from pinned tasks for consistent slot calculations
            base_date = None
            pinned_tasks = task_df[task_df.get("Pinned", False) == True]
            if not pinned_tasks.empty:
                # Try to determine base_date from earliest pinned task
                earliest_date = None
                for _, row in pinned_tasks.iterrows():
                    start_time = row.get("Start")
                    if start_time is not None:
                        try:
                            if isinstance(start_time, str):
                                dt = datetime.fromisoformat(
                                    start_time.replace("Z", "+00:00")
                                )
                            elif isinstance(start_time, pd.Timestamp):
                                dt = start_time.to_pydatetime()
                            elif isinstance(start_time, datetime):
                                dt = start_time
                            elif isinstance(start_time, (int, float)):
                                # Handle Unix timestamp (milliseconds or seconds)
                                if start_time > 1e10:
                                    dt = datetime.fromtimestamp(
                                        start_time / 1000, tz=timezone.utc
                                    ).replace(tzinfo=None)
                                else:
                                    dt = datetime.fromtimestamp(
                                        start_time, tz=timezone.utc
                                    ).replace(tzinfo=None)
                            else:
                                logger.debug(
                                    f"Unhandled start_time type for base_date: {type(start_time)} = {start_time}"
                                )
                                continue

                            if earliest_date is None or dt.date() < earliest_date:
                                earliest_date = dt.date()
                        except Exception as e:
                            logger.debug(f"Error parsing start_time for base_date: {e}")
                            continue

                if earliest_date:
                    base_date = earliest_date
                    logger.info(f"🗓️ Determined base_date for schedule: {base_date}")

            # If no base_date found from pinned tasks, use next Monday as default
            if base_date is None:
                from factory.data.generators import earliest_monday_on_or_after

                base_date = earliest_monday_on_or_after(date.today())
                logger.info(
                    f"🗓️ No pinned tasks found, using next Monday as base_date: {base_date}"
                )

            # Convert DataFrame to tasks
            tasks = DataService.convert_dataframe_to_tasks(task_df, base_date)

            # Debug: Log task information if debug is enabled
            if debug:
                logger.info("🔍 DEBUG: Task information for constraint checking:")

                for task in tasks:
                    logger.info(
                        f"  Task ID: {task.id}, Project: '{task.project_id}', "
                        f"Sequence: {task.sequence_number}, Description: '{task.description[:30]}...'"
                    )

            # Generate schedule
            schedule = ScheduleService.generate_schedule_for_solving(
                tasks, employee_count, days_in_schedule, base_date
            )

            # Start solving
            (
                emp_df,
                solved_task_df,
                new_job_id,
                status,
            ) = ScheduleService.solve_schedule(schedule, debug)

            logger.info("📈 Solver process initiated successfully")
            return emp_df, solved_task_df, new_job_id, status, state_data

        except Exception as e:
            logger.error(f"Error in solve_schedule_from_state: {e}")

            return (
                gr.update(),
                gr.update(),
                None,
                f"Error solving schedule: {str(e)}",
                state_data,
            )

    @staticmethod
    def generate_schedule_for_solving(
        tasks: list,
        employee_count: Optional[int],
        days_in_schedule: Optional[int],
        base_date: date = None,
    ) -> EmployeeSchedule:
        """Generate a complete schedule ready for solving"""
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

        logger.info("👥 Generating employees and availability...")
        start_date = datetime.now().date()

        randomizer = random.Random(parameters.random_seed)

        # Analyze tasks to determine what skills are actually needed
        required_skills_needed = set()
        for task in tasks:
            if hasattr(task, "required_skill") and task.required_skill:
                required_skills_needed.add(task.required_skill)

        logger.info(f"🔍 Tasks require skills: {sorted(required_skills_needed)}")

        # Generate employees with skills needed for the tasks
        employees = generate_employees(parameters, randomizer, required_skills_needed)

        # For single employee scenarios, set name and clear availability constraints
        if parameters.employee_count == 1 and len(employees) == 1:
            employees[0].name = "Chatbot User"
            employees[0].unavailable_dates.clear()
            employees[0].undesired_dates.clear()
            employees[0].desired_dates.clear()

        else:
            # Generate employee availability preferences for multi-employee scenarios
            logger.info("📅 Generating employee availability preferences...")
            generate_employee_availability(
                employees, parameters, start_date, randomizer
            )
            logger.info("✅ Employee availability generated")

        logger.info(f"✅ Generated {len(employees)} employees")

        # Assign employees to all tasks (both pinned and non-pinned)
        # For single employee scenarios, assign the single employee to all tasks
        if parameters.employee_count == 1 and len(employees) == 1:
            main_employee = employees[0]
            for task in tasks:
                task.employee = main_employee
                logger.debug(
                    f"Assigned {main_employee.name} to task: {task.description[:30]}..."
                )
        else:
            # For multi-employee scenarios, assign employees based on skills and availability
            # This is a simple assignment - the solver will optimize later
            for task in tasks:
                # Find an employee with the required skill
                suitable_employees = [
                    emp for emp in employees if task.required_skill in emp.skills
                ]
                if suitable_employees:
                    task.employee = suitable_employees[0]  # Simple assignment
                else:
                    # Fallback: assign the first employee
                    task.employee = employees[0]
                    logger.warning(
                        f"No employee found with skill '{task.required_skill}' for task '{task.description[:30]}...', assigned {employees[0].name}"
                    )

        logger.info(f"✅ Assigned employees to {len(tasks)} tasks")

        return EmployeeSchedule(
            employees=employees,
            tasks=tasks,
            schedule_info=ScheduleInfo(
                total_slots=parameters.days_in_schedule * SLOTS_PER_WORKING_DAY,
                base_date=base_date,
            ),
        )

    @staticmethod
    def solve_schedule(
        schedule: EmployeeSchedule, debug: bool = False
    ) -> Tuple[pd.DataFrame, pd.DataFrame, str, str]:
        """
        Solve the schedule and return the dataframes and job_id.

        Args:
            schedule: The schedule to solve
            debug: Enable debug logging

        Returns:
            Tuple of (emp_df, task_df, job_id, status_message)
        """
        if schedule is None:
            return None, None, None, "No schedule to solve. Please load data first."

        job_id: str = str(uuid.uuid4())

        # Start solving asynchronously
        def listener(solution):
            StateService.store_solved_schedule(job_id, solution)

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
                "Pinned",
            ]
        ].sort_values(["Project", "Sequence"])

        return emp_df, task_df, job_id, "Solving..."

    @staticmethod
    def poll_solution(
        job_id: str, schedule: EmployeeSchedule, debug: bool = False
    ) -> Tuple[pd.DataFrame, pd.DataFrame, str, str, object]:
        """
        Poll for a solution for a given job_id.

        Args:
            job_id: The job_id to poll for
            schedule: The current schedule state
            debug: Whether to enable debug logging

        Returns:
            Tuple of (emp_df, task_df, job_id, status_message, schedule)
        """
        if job_id and StateService.has_solved_schedule(job_id):
            solved_schedule: EmployeeSchedule = StateService.get_solved_schedule(job_id)

            emp_df: pd.DataFrame = employees_to_dataframe(solved_schedule)
            task_df: pd.DataFrame = schedule_to_dataframe(solved_schedule)

            if debug:
                # Log solved task order for debugging
                logger.info("Solved task order:")

                for _, row in task_df.iterrows():
                    logger.info(
                        f"Project: {row['Project']}, Sequence: {row['Sequence']}, Task: {row['Task'][:30]}, Start: {row['Start']}"
                    )

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
                    "Pinned",
                ]
            ].sort_values(["Start"])

            # Check if hard constraints are violated (infeasible solution)
            status_message = ScheduleService.generate_status_message(solved_schedule)

            return emp_df, task_df, job_id, status_message, solved_schedule

        return None, None, job_id, "Solving...", schedule

    @staticmethod
    async def auto_poll(
        job_id: str, llm_output: dict, debug: bool = False
    ) -> Tuple[pd.DataFrame, pd.DataFrame, str, str, dict]:
        """
        Poll for updates asynchronously.

        Args:
            job_id: Job identifier to poll for
            llm_output: Current LLM output state
            debug: Enable debug logging

        Returns:
            Tuple of (emp_df, task_df, job_id, status_message, llm_output)
        """
        try:
            if job_id and StateService.has_solved_schedule(job_id):
                schedule = StateService.get_solved_schedule(job_id)
                emp_df = employees_to_dataframe(schedule)
                task_df = schedule_to_dataframe(schedule)

                # Sort tasks by start time for display
                task_df = task_df.sort_values("Start")

                if debug:
                    logger.info(f"Polling for job {job_id}")
                    logger.info(f"Current schedule state: {task_df.head()}")

                # Generate status message based on constraint satisfaction
                status_message = ScheduleService.generate_status_message(schedule)

                return emp_df, task_df, job_id, status_message, llm_output

        except Exception as e:
            logger.error(f"Error polling: {e}")
            return (
                gr.update(),
                gr.update(),
                job_id,
                f"Error polling: {str(e)}",
                llm_output,
            )

        return (
            gr.update(),
            gr.update(),
            None,
            "No updates",
            llm_output,
        )

    @staticmethod
    def generate_status_message(schedule: EmployeeSchedule) -> str:
        """Generate status message based on schedule score and constraint violations"""
        status_message = "Solution updated"

        if schedule.score is not None:
            hard_score = schedule.score.hard_score
            if hard_score < 0:
                # Hard constraints are violated - the problem is infeasible
                violation_count = abs(int(hard_score))

                violation_details = (
                    ConstraintAnalyzerService.analyze_constraint_violations(schedule)
                )

                suggestions = (
                    ConstraintAnalyzerService.generate_improvement_suggestions(schedule)
                )

                suggestion_text = "\n".join(f"• {s}" for s in suggestions)

                status_message = (
                    f"⚠️ CONSTRAINTS VIOLATED: {violation_count} hard constraint(s) could not be satisfied. "
                    f"The schedule is not feasible.\n\n{violation_details}\n\nSuggestions:\n{suggestion_text}"
                )

                logger.warning(
                    f"Infeasible solution detected. Hard score: {hard_score}"
                )

            else:
                soft_score = schedule.score.soft_score
                status_message = f"✅ Solved successfully! Score: {hard_score}/{soft_score} (hard/soft)"
                logger.info(
                    f"Feasible solution found. Score: {hard_score}/{soft_score}"
                )

        return status_message

    @staticmethod
    def start_timer(job_id: str, llm_output: Any) -> gr.Timer:
        """Start a timer for polling (Gradio-specific functionality)"""
        return gr.Timer(active=True)
