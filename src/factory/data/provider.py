import os
import pandas as pd

from datetime import date
from random import Random

pd.set_option("display.max_columns", None)
from factory.data.formatters import schedule_to_dataframe

from factory.data.generators import *
from factory.data.models import *

from factory.agents.task_composer_agent import TaskComposerAgent

from constraint_solvers.timetable.domain import *

from utils.logging_config import setup_logging, get_logger
from utils.extract_calendar import (
    get_earliest_calendar_date,
    datetime_to_slot,
    validate_calendar_working_hours,
)

# Initialize logging
setup_logging()
logger = get_logger(__name__)

# =========================
#        CONSTANTS
# =========================

# Import working hours configuration
from constraint_solvers.timetable.working_hours import SLOTS_PER_WORKING_DAY


# =========================
#        DEMO PARAMS
# =========================
SKILL_SET = SkillSet(
    required_skills=("Frontend Engineer", "Backend Engineer", "Cloud Engineer"),
    optional_skills=(
        "Security Expert",
        "DevOps Engineer",
        "Data Engineer",
        "Network Engineer",
        "AI Engineer",
    ),
)

DATA_PARAMS = TimeTableDataParameters(
    skill_set=SKILL_SET,
    days_in_schedule=365,
    employee_count=12,
    optional_skill_distribution=(
        CountDistribution(count=1, weight=3),
        CountDistribution(count=2, weight=1),
    ),
    availability_count_distribution=(
        CountDistribution(count=5, weight=4),
        CountDistribution(count=10, weight=3),
        CountDistribution(count=15, weight=2),
        CountDistribution(count=20, weight=1),
    ),
    random_seed=37,
)

MCP_PARAMS = TimeTableDataParameters(
    skill_set=SKILL_SET,
    days_in_schedule=365,
    # In this case, we only have one user
    employee_count=1,
    optional_skill_distribution=(
        CountDistribution(count=len(SKILL_SET.optional_skills), weight=1),
    ),
    availability_count_distribution=(
        # Full availability for one user
        CountDistribution(count=20, weight=1),
    ),
    random_seed=37,
)


# =========================
#        AGENT DATA
# =========================
async def generate_agent_data(
    file, project_id: str = "", employee_count: int = None, days_in_schedule: int = None
) -> EmployeeSchedule:
    # Use DATA_PARAMS, but allow override
    parameters = DATA_PARAMS
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

    start_date: date = earliest_monday_on_or_after(date.today())
    randomizer: Random = Random(parameters.random_seed)
    employees: list[Employee] = generate_employees(parameters, randomizer)
    total_slots: int = parameters.days_in_schedule * SLOTS_PER_WORKING_DAY

    logger.debug("Processing file object: %s (type: %s)", file, type(file))

    match file:
        case file if hasattr(file, "read"):
            input_str = file.read()

        case bytes():
            input_str = file.decode("utf-8")

        case str() if os.path.exists(file):
            with open(file, "r", encoding="utf-8") as f:
                input_str = f.read()

        case str():
            input_str = file

        case _:
            raise ValueError(f"Unsupported file type: {type(file)}")

    agent_output = await run_task_composer_agent(input_str, parameters)

    tasks = tasks_from_agent_output(agent_output, parameters, project_id)
    generate_employee_availability(employees, parameters, start_date, randomizer)

    return EmployeeSchedule(
        employees=employees,
        tasks=tasks,
        schedule_info=ScheduleInfo(total_slots=total_slots),
    )


async def generate_mcp_data(
    calendar_entries,
    user_message: str,
    project_id: str = "PROJECT",
    employee_count: int = None,
    days_in_schedule: int = None,
):
    parameters = MCP_PARAMS

    # --- DETERMINE START DATE AND REQUIRED SCHEDULE LENGTH FROM CALENDAR ---

    # Validate calendar entries are within working hours first
    if calendar_entries:
        is_valid, error_msg = validate_calendar_working_hours(calendar_entries)
        if not is_valid:
            logger.error(f"❌ Calendar validation failed: {error_msg}")
            raise ValueError(
                f"Calendar entries violate working hours constraints:\n{error_msg}"
            )
        else:
            logger.info(
                f"✅ All {len(calendar_entries)} calendar entries are within working hours (8:00-18:00)"
            )

    # Use earliest calendar date as the base, or fall back to next Monday if no calendar
    earliest_calendar_date = (
        get_earliest_calendar_date(calendar_entries) if calendar_entries else None
    )

    if earliest_calendar_date:
        start_date: date = earliest_calendar_date

        # Calculate required schedule length to accommodate all calendar entries
        if calendar_entries and days_in_schedule is None:
            # Find the latest calendar date to determine required schedule length
            latest_date = earliest_calendar_date
            for entry in calendar_entries:
                end_dt = entry.get("end_datetime")
                if end_dt and end_dt.date() > latest_date:
                    latest_date = end_dt.date()

            # Calculate days needed plus buffer for LLM tasks
            calendar_days_span = (latest_date - earliest_calendar_date).days + 1
            min_required_days = (
                calendar_days_span + 30
            )  # Add 30 days buffer for LLM tasks

            # Use the larger of user-specified or calculated requirement
            calculated_days = max(min_required_days, parameters.days_in_schedule)
            logger.info(
                f"📊 Calendar span: {calendar_days_span} days, using {calculated_days} total schedule days"
            )
        else:
            calculated_days = (
                days_in_schedule if days_in_schedule else parameters.days_in_schedule
            )
    else:
        start_date: date = earliest_monday_on_or_after(date.today())
        calculated_days = (
            days_in_schedule if days_in_schedule else parameters.days_in_schedule
        )

    # Update parameters with calculated values
    if employee_count is not None or calculated_days != parameters.days_in_schedule:
        parameters = TimeTableDataParameters(
            skill_set=parameters.skill_set,
            days_in_schedule=calculated_days,
            employee_count=employee_count
            if employee_count is not None
            else parameters.employee_count,
            optional_skill_distribution=parameters.optional_skill_distribution,
            availability_count_distribution=parameters.availability_count_distribution,
            random_seed=parameters.random_seed,
        )

    randomizer: Random = Random(parameters.random_seed)
    total_slots: int = parameters.days_in_schedule * SLOTS_PER_WORKING_DAY

    # --- CALENDAR TASKS ---
    calendar_tasks = generate_tasks_from_calendar(
        parameters, randomizer, calendar_entries, base_date=start_date
    )

    # Validate that all calendar tasks have valid slot assignments
    for task in calendar_tasks:
        if task.start_slot >= total_slots:
            logger.error(
                f"Calendar task '{task.description}' has slot {task.start_slot} >= {total_slots}"
            )
            raise ValueError(
                f"Calendar task slot {task.start_slot} exceeds schedule length {total_slots}. "
                f"Increase days_in_schedule or check calendar dates."
            )

    # Assign project_id 'EXISTING' to all calendar tasks
    for t in calendar_tasks:
        t.sequence_number = 0  # will be overwritten later
        t.project_id = "EXISTING"

    # --- LLM TASKS ---
    llm_tasks = []
    if user_message:
        agent_output = await run_task_composer_agent(user_message, parameters)
        llm_tasks = tasks_from_agent_output(agent_output, parameters, "PROJECT")
        for t in llm_tasks:
            t.sequence_number = 0  # will be overwritten later
            t.project_id = "PROJECT"

    # --- ANALYZE REQUIRED SKILLS ---
    all_tasks = calendar_tasks + llm_tasks
    required_skills_needed = set()
    for task in all_tasks:
        if hasattr(task, "required_skill") and task.required_skill:
            required_skills_needed.add(task.required_skill)

    # --- GENERATE EMPLOYEES WITH REQUIRED SKILLS ---
    employees: list[Employee] = generate_employees(
        parameters, randomizer, required_skills_needed
    )

    # Set the single employee's name to 'Chatbot User'
    if len(employees) == 1:
        employees[0].name = "Chatbot User"

    else:
        raise ValueError("MCP data provider only supports one employee")

    # Ensure all date sets are empty
    for emp in employees:
        emp.unavailable_dates.clear()
        emp.undesired_dates.clear()
        emp.desired_dates.clear()

    # --- ASSIGN EMPLOYEES TO TASKS ---
    for t in all_tasks:
        t.employee = employees[0]

    # Create DataFrames for debugging
    calendar_df = pd.DataFrame(
        [
            {
                "id": t.id,
                "description": t.description,
                "duration_slots": t.duration_slots,
                "start_slot": t.start_slot,
                "required_skill": t.required_skill,
                "sequence_number": t.sequence_number,
                "employee": t.employee.name if hasattr(t.employee, "name") else None,
                "project_id": t.project_id,
            }
            for t in calendar_tasks
        ]
    )

    logger.debug("Generated calendar tasks DataFrame:\n%s", calendar_df)

    llm_df = pd.DataFrame(
        [
            {
                "id": t.id,
                "description": t.description,
                "duration_slots": t.duration_slots,
                "start_slot": t.start_slot,
                "required_skill": t.required_skill,
                "sequence_number": t.sequence_number,
                "employee": t.employee.name if hasattr(t.employee, "name") else None,
                "project_id": t.project_id,
            }
            for t in llm_tasks
        ]
    )

    logger.debug("Generated LLM tasks DataFrame:\n%s", llm_df)

    # --- ASSIGN SEQUENCE NUMBERS ---
    existing_seq = 0
    project_seq = 0
    for t in all_tasks:
        if t.project_id == "EXISTING":
            t.sequence_number = existing_seq
            existing_seq += 1
        elif t.project_id == "PROJECT":
            t.sequence_number = project_seq
            project_seq += 1

    schedule = EmployeeSchedule(
        employees=employees,
        tasks=all_tasks,
        schedule_info=ScheduleInfo(
            total_slots=total_slots, base_date=start_date, base_timezone=None
        ),
    )

    final_df = schedule_to_dataframe(schedule)

    logger.debug("Final schedule DataFrame (MCP-aligned):\n%s", final_df)

    return final_df


async def run_task_composer_agent(
    input_str: str, parameters: TimeTableDataParameters
) -> list:
    """Runs the task composition agent with the given input and parameters."""
    try:
        # Initialize the agent
        agent = TaskComposerAgent()

        # Run the agent with the input
        output = await agent.compose_tasks(input_str, parameters)

        logger.debug("Agent output: %s", output)
        return output

    except Exception as e:
        logger.error("Error running task composer agent: %s", e)
        # Return empty list on error
        return []
