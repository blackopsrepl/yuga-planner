import uuid
import logging
import random
from datetime import datetime
from typing import Tuple, Dict, Any, Optional

import pandas as pd
import gradio as gr

from state import app_state
from constraint_solvers.timetable.solver import solver_manager
from factory.data_provider import (
    generate_employees,
    generate_employee_availability,
    DATA_PARAMS,
    TimeTableDataParameters,
    SLOTS_PER_DAY,
)

from constraint_solvers.timetable.domain import (
    EmployeeSchedule,
    ScheduleInfo,
    Task,
)

from helpers import schedule_to_dataframe, employees_to_dataframe
from .data_service import DataService
from constraint_solvers.timetable.analysis import ConstraintViolationAnalyzer


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
        logging.info(f"🔧 solve_schedule_from_state called with job_id: {job_id}")
        logging.info("🚀 Starting solve process...")

        # Set debug environment variable for constraint system
        import os

        if debug:
            os.environ["YUGA_DEBUG"] = "true"
        else:
            os.environ["YUGA_DEBUG"] = "false"

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

        if not task_df_json:
            logging.warning("❌ No task_df_json provided to solve_schedule_from_state")
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

            # Convert DataFrame to tasks
            tasks = DataService.convert_dataframe_to_tasks(task_df)

            # Debug: Log task information if debug is enabled
            if debug:
                logging.info("🔍 DEBUG: Task information for constraint checking:")
                for task in tasks:
                    logging.info(
                        f"  Task ID: {task.id}, Project: '{task.project_id}', "
                        f"Sequence: {task.sequence_number}, Description: '{task.description[:30]}...'"
                    )

            # Generate schedule
            schedule = ScheduleService._generate_schedule_for_solving(
                tasks, employee_count, days_in_schedule
            )

            # Start solving
            (
                emp_df,
                solved_task_df,
                new_job_id,
                status,
            ) = await ScheduleService._solve_schedule(schedule, debug)

            logging.info("📈 Solver process initiated successfully")
            return emp_df, solved_task_df, new_job_id, status, state_data

        except Exception as e:
            logging.error(f"Error in solve_schedule_from_state: {e}")
            return (
                gr.update(),
                gr.update(),
                None,
                f"Error solving schedule: {str(e)}",
                state_data,
            )

    @staticmethod
    def _generate_schedule_for_solving(
        tasks: list, employee_count: Optional[int], days_in_schedule: Optional[int]
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

        logging.info("👥 Generating employees and availability...")
        start_date = datetime.now().date()
        randomizer = random.Random(parameters.random_seed)
        employees = generate_employees(parameters, randomizer)
        logging.info(f"✅ Generated {len(employees)} employees")

        # Generate employee availability preferences
        logging.info("📅 Generating employee availability preferences...")
        generate_employee_availability(employees, parameters, start_date, randomizer)
        logging.info("✅ Employee availability generated")

        return EmployeeSchedule(
            employees=employees,
            tasks=tasks,
            schedule_info=ScheduleInfo(
                total_slots=parameters.days_in_schedule * SLOTS_PER_DAY
            ),
        )

    @staticmethod
    async def _solve_schedule(
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
            ].sort_values(["Start"])

            # Check if hard constraints are violated (infeasible solution)
            status_message = ScheduleService._generate_status_message(solved_schedule)

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
            if job_id and app_state.has_solved_schedule(job_id):
                schedule = app_state.get_solved_schedule(job_id)
                emp_df = employees_to_dataframe(schedule)
                task_df = schedule_to_dataframe(schedule)

                # Sort tasks by start time for display
                task_df = task_df.sort_values("Start")

                if debug:
                    logging.info(f"Polling for job {job_id}")
                    logging.info(f"Current schedule state: {task_df.head()}")

                # Generate status message based on constraint satisfaction
                status_message = ScheduleService._generate_status_message(schedule)

                return emp_df, task_df, job_id, status_message, llm_output

        except Exception as e:
            logging.error(f"Error polling: {e}")
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
    def _generate_status_message(schedule: EmployeeSchedule) -> str:
        """Generate status message based on schedule score and constraint violations"""
        status_message = "Solution updated"

        if schedule.score is not None:
            hard_score = schedule.score.hard_score
            if hard_score < 0:
                # Hard constraints are violated - the problem is infeasible
                violation_count = abs(int(hard_score))
                violation_details = (
                    ConstraintViolationAnalyzer.analyze_constraint_violations(schedule)
                )
                suggestions = ConstraintViolationAnalyzer.generate_suggestions(schedule)
                suggestion_text = "\n".join(f"• {s}" for s in suggestions)

                status_message = (
                    f"⚠️ CONSTRAINTS VIOLATED: {violation_count} hard constraint(s) could not be satisfied. "
                    f"The schedule is not feasible.\n\n{violation_details}\n\nSuggestions:\n{suggestion_text}"
                )
                logging.warning(
                    f"Infeasible solution detected. Hard score: {hard_score}"
                )
            else:
                soft_score = schedule.score.soft_score
                status_message = f"✅ Solved successfully! Score: {hard_score}/{soft_score} (hard/soft)"
                logging.info(
                    f"Feasible solution found. Score: {hard_score}/{soft_score}"
                )

        return status_message

    @staticmethod
    def start_timer(job_id: str, llm_output: Any) -> gr.Timer:
        """Start a timer for polling (Gradio-specific functionality)"""
        return gr.Timer(active=True)
