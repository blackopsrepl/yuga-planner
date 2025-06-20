import os
import uuid
from io import StringIO
from typing import Dict, List, Tuple, Union, Optional, Any
from datetime import datetime, date, timezone

import pandas as pd

from factory.data.provider import (
    generate_agent_data,
    DATA_PARAMS,
    TimeTableDataParameters,
)
from constraint_solvers.timetable.working_hours import SLOTS_PER_WORKING_DAY

from constraint_solvers.timetable.domain import (
    EmployeeSchedule,
    ScheduleInfo,
    Task,
    Employee,
)

from factory.data.formatters import schedule_to_dataframe, employees_to_dataframe
from .mock_projects import MockProjectService
from utils.logging_config import setup_logging, get_logger
from utils.extract_calendar import datetime_to_slot, get_earliest_calendar_date

# Initialize logging
setup_logging()
logger = get_logger(__name__)


class DataService:
    """Service for handling data loading and processing operations"""

    @staticmethod
    async def load_data_from_sources(
        project_source: str,
        file_obj: Any,
        mock_projects: Union[str, List[str], None],
        employee_count: int,
        days_in_schedule: int,
        debug: bool = False,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, str, str, Dict[str, Any]]:
        """
        Handle data loading from either file uploads or mock projects.

        Args:
            project_source: Source type ("Upload Project Files" or mock projects)
            file_obj: Uploaded file object(s)
            mock_projects: Selected mock project names
            employee_count: Number of employees to generate
            days_in_schedule: Number of days in the schedule
            debug: Enable debug logging

        Returns:
            Tuple of (emp_df, task_df, job_id, status_message, state_data)
        """
        if project_source == "Upload Project Files":
            files, project_source_info = DataService.process_uploaded_files(file_obj)

        else:
            files, project_source_info = DataService.process_mock_projects(
                mock_projects
            )

        logger.info(f"🔄 Processing {len(files)} project(s)...")

        combined_tasks: List[Task] = []
        combined_employees: Dict[str, Employee] = {}

        # Process each file/project
        for idx, single_file in enumerate(files):
            project_id = DataService.derive_project_id(
                project_source, single_file, mock_projects, idx
            )

            logger.info(f"⚙️ Processing project {idx+1}/{len(files)}: '{project_id}'")

            schedule_part: EmployeeSchedule = await generate_agent_data(
                single_file,
                project_id=project_id,
                employee_count=employee_count,
                days_in_schedule=days_in_schedule,
            )

            logger.info(f"✅ Completed processing project '{project_id}'")

            # Merge employees (unique by name)
            for emp in schedule_part.employees:
                if emp.name not in combined_employees:
                    combined_employees[emp.name] = emp

            # Append tasks with project id already set
            combined_tasks.extend(schedule_part.tasks)

        logger.info(
            f"👥 Merging data: {len(combined_employees)} unique employees, {len(combined_tasks)} total tasks"
        )

        # Build final schedule
        final_schedule = DataService.build_final_schedule(
            combined_employees, combined_tasks, employee_count, days_in_schedule
        )

        # Convert to DataFrames
        emp_df, task_df = DataService.convert_to_dataframes(final_schedule, debug)

        # Generate job ID and state data
        job_id = str(uuid.uuid4())
        state_data = {
            "task_df_json": task_df.to_json(orient="split"),
            "employee_count": employee_count,
            "days_in_schedule": days_in_schedule,
        }

        status_message = f"Data loaded successfully from {project_source_info}"
        logger.info("🎉 Data loading completed successfully!")

        return emp_df, task_df, job_id, status_message, state_data

    @staticmethod
    def process_uploaded_files(file_obj: Any) -> Tuple[List[Any], str]:
        """Process uploaded files and return file list and description"""
        if file_obj is None:
            raise ValueError("No file uploaded. Please upload a file.")

        # Support multiple files. Gradio returns a list when multiple files are selected.
        files = file_obj if isinstance(file_obj, list) else [file_obj]
        project_source_info = f"{len(files)} file(s)"
        logger.info(f"📄 Found {len(files)} file(s) to process")

        return files, project_source_info

    @staticmethod
    def process_mock_projects(
        mock_projects: Union[str, List[str], None]
    ) -> Tuple[List[str], str]:
        """Process mock projects and return file contents and description"""
        if not mock_projects:
            raise ValueError("Please select at least one mock project.")

        # Ensure mock_projects is a list
        if isinstance(mock_projects, str):
            mock_projects = [mock_projects]

        # Validate all selected mock projects
        invalid_projects = MockProjectService.validate_mock_projects(mock_projects)
        if invalid_projects:
            raise ValueError(
                f"Invalid mock projects selected: {', '.join(invalid_projects)}"
            )

        # Get file contents for mock projects
        files = MockProjectService.get_mock_project_files(mock_projects)
        project_source_info = (
            f"{len(mock_projects)} mock project(s): {', '.join(mock_projects)}"
        )
        logger.info(f"📋 Selected mock projects: {', '.join(mock_projects)}")

        return files, project_source_info

    @staticmethod
    def derive_project_id(
        project_source: str,
        single_file: Any,
        mock_projects: Union[str, List[str], None],
        idx: int,
    ) -> str:
        """Derive project ID from file or mock project"""
        if project_source == "Upload Project Files":
            try:
                return os.path.splitext(os.path.basename(single_file.name))[0]

            except AttributeError:
                return f"project_{idx+1}"

        else:
            # For mock projects, use the mock project name as the project ID
            if isinstance(mock_projects, list):
                return mock_projects[idx]

            return mock_projects or f"project_{idx+1}"

    @staticmethod
    def build_final_schedule(
        combined_employees: Dict[str, Employee],
        combined_tasks: List[Task],
        employee_count: Optional[int],
        days_in_schedule: Optional[int],
    ) -> EmployeeSchedule:
        """Build the final schedule with custom parameters if provided"""
        parameters: TimeTableDataParameters = DATA_PARAMS

        # Override with custom parameters if provided
        if employee_count is not None or days_in_schedule is not None:
            logger.info(
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

        logger.info("🏗️ Building final schedule structure...")

        return EmployeeSchedule(
            employees=list(combined_employees.values()),
            tasks=combined_tasks,
            schedule_info=ScheduleInfo(
                total_slots=parameters.days_in_schedule * SLOTS_PER_WORKING_DAY,
                base_date=None,  # Use default base_date for regular data loading
            ),
        )

    @staticmethod
    def convert_to_dataframes(
        schedule: EmployeeSchedule, debug: bool = False
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Convert schedule to DataFrames for display"""
        logger.info("📊 Converting to data tables...")
        emp_df: pd.DataFrame = employees_to_dataframe(schedule)
        task_df: pd.DataFrame = schedule_to_dataframe(schedule)

        # Sort by project and sequence to maintain original order
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

        if debug:
            # Log sequence numbers for debugging
            logger.info("Task sequence numbers after load_data:")
            for _, row in task_df.iterrows():
                logger.info(
                    f"Project: {row['Project']}, Sequence: {row['Sequence']}, Task: {row['Task']}"
                )
            logger.info("Task DataFrame being set in load_data: %s", task_df.head())

        return emp_df, task_df

    @staticmethod
    def parse_task_data_from_json(
        task_df_json: str, debug: bool = False
    ) -> pd.DataFrame:
        """
        Parse task data from JSON string.

        Args:
            task_df_json: JSON string containing task data
            debug: Enable debug logging

        Returns:
            DataFrame containing task data
        """
        if not task_df_json:
            raise ValueError("No task_df_json provided")

        try:
            logger.info("📋 Parsing task data from JSON...")
            task_df: pd.DataFrame = pd.read_json(StringIO(task_df_json), orient="split")
            logger.info(f"📊 Found {len(task_df)} tasks to schedule")

            if debug:
                logger.info("Task sequence numbers from JSON:")

                for _, row in task_df.iterrows():
                    logger.info(
                        f"Project: {row.get('Project', 'N/A')}, Sequence: {row.get('Sequence', 'N/A')}, Task: {row['Task']}"
                    )

            return task_df

        except Exception as e:
            logger.error(f"❌ Error parsing task_df_json: {e}")
            raise ValueError(f"Error parsing task data: {str(e)}")

    @staticmethod
    def convert_dataframe_to_tasks(
        task_df: pd.DataFrame, base_date: date = None
    ) -> List[Task]:
        """
        Convert a DataFrame to a list of Task objects.

        Args:
            task_df: DataFrame containing task data
            base_date: Base date for slot calculations (for pinned tasks)

        Returns:
            List of Task objects
        """
        logger.info("🆔 Generating task IDs and converting to solver format...")
        ids = (str(i) for i in range(len(task_df)))

        # Determine base_date if not provided
        if base_date is None:
            # Try to get from pinned tasks' dates
            pinned_tasks = task_df[task_df.get("Pinned", False) == True]
            if not pinned_tasks.empty:
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
                    logger.info(f"Determined base_date from pinned tasks: {base_date}")
                else:
                    base_date = date.today()
                    logger.warning(
                        "Could not determine base_date from pinned tasks, using today"
                    )
            else:
                base_date = date.today()

        tasks = []
        for _, row in task_df.iterrows():
            # Check if task is pinned and should preserve its start_slot
            is_pinned = row.get("Pinned", False)

            # For pinned tasks, calculate start_slot from the Start datetime
            if is_pinned and "Start" in row and row["Start"] is not None:
                try:
                    start_time = row["Start"]

                    # Handle different datetime formats
                    if isinstance(start_time, str):
                        # Parse ISO string
                        start_time = datetime.fromisoformat(
                            start_time.replace("Z", "+00:00")
                        )
                    elif isinstance(start_time, pd.Timestamp):
                        # Convert pandas Timestamp to datetime
                        start_time = start_time.to_pydatetime()
                    elif isinstance(start_time, (int, float)):
                        # Handle Unix timestamp (milliseconds or seconds)
                        try:
                            # If it's a large number, assume milliseconds
                            if start_time > 1e10:
                                start_time = datetime.fromtimestamp(
                                    start_time / 1000, tz=timezone.utc
                                ).replace(tzinfo=None)
                            else:
                                start_time = datetime.fromtimestamp(
                                    start_time, tz=timezone.utc
                                ).replace(tzinfo=None)
                        except (ValueError, OSError) as e:
                            logger.warning(
                                f"Cannot convert timestamp {start_time} to datetime: {e}"
                            )
                            start_slot = 0
                    elif not isinstance(start_time, datetime):
                        # Skip conversion if we can't parse the datetime
                        logger.warning(
                            f"Cannot parse start time for pinned task: {start_time} (type: {type(start_time)})"
                        )
                        start_slot = 0

                    if isinstance(start_time, datetime):
                        start_slot = datetime_to_slot(start_time, base_date)
                        logger.info(
                            f"Converted datetime {start_time} to slot {start_slot} for pinned task (base: {base_date})"
                        )
                    else:
                        start_slot = 0

                except Exception as e:
                    logger.warning(
                        f"Error converting datetime to slot for pinned task: {e}"
                    )
                    start_slot = 0
            else:
                start_slot = 0  # Will be assigned by solver for non-pinned tasks

            tasks.append(
                Task(
                    id=next(ids),
                    description=row["Task"],
                    duration_slots=int(float(row["Duration (hours)"]) * 2),
                    start_slot=start_slot,
                    required_skill=row["Required Skill"],
                    project_id=row.get("Project", ""),
                    sequence_number=int(row.get("Sequence", 0)),
                    pinned=is_pinned,
                    employee=None,  # Will be assigned in generate_schedule_for_solving
                )
            )

        logger.info(
            f"✅ Converted {len(tasks)} tasks for solver (base_date: {base_date})"
        )
        return tasks
