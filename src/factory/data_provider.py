import os
import pandas as pd

pd.set_option("display.max_columns", None)
from helpers import schedule_to_dataframe

from datetime import date
from random import Random

from domain import AGENTS_CONFIG

from factory.data_generators import *
from factory.data_models import *

from agents.task_composer_agent import TaskComposerAgent

from constraint_solvers.timetable.domain import *

import logging

logging.basicConfig(level=logging.INFO)

# =========================
#        CONSTANTS
# =========================

# Each slot is 30 minutes - 20 slots = 10 hours working day
SLOTS_PER_DAY = 20


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
    total_slots: int = parameters.days_in_schedule * SLOTS_PER_DAY

    if os.getenv("YUGA_DEBUG", "false").lower() == "true":
        logging.info("FILE OBJECT: %s %s", file, type(file))

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
    total_slots: int = parameters.days_in_schedule * SLOTS_PER_DAY

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

    # --- CALENDAR TASKS ---
    calendar_tasks = generate_tasks_from_calendar(
        parameters, randomizer, calendar_entries
    )
    # Assign project_id 'EXISTING' to all calendar tasks
    for t in calendar_tasks:
        t.sequence_number = 0  # will be overwritten later
        t.employee = employees[0]
        t.project_id = "EXISTING"
    # Create DataFrame
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

    print("\nCalendar DataFrame:")
    print(calendar_df)

    # --- LLM TASKS ---
    llm_tasks = []
    if user_message:
        from factory.data_provider import run_task_composer_agent

        agent_output = await run_task_composer_agent(user_message, parameters)
        llm_tasks = tasks_from_agent_output(agent_output, parameters, "PROJECT")
        for t in llm_tasks:
            t.sequence_number = 0  # will be overwritten later
            t.employee = employees[0]
            t.project_id = "PROJECT"
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

    print("\nLLM DataFrame:")
    print(llm_df)

    # --- MERGE AND ASSIGN SEQUENCE ---
    all_tasks = calendar_tasks + llm_tasks
    # Assign sequence_number per project group
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
        schedule_info=ScheduleInfo(total_slots=total_slots),
    )
    final_df = schedule_to_dataframe(schedule)
    print("\nFinal DataFrame (MCP-aligned):")
    print(final_df)
    return final_df


async def run_task_composer_agent(
    input_str: str, parameters: TimeTableDataParameters
) -> list:
    agent = TaskComposerAgent(AGENTS_CONFIG)
    available_skills = list(parameters.skill_set.required_skills) + list(
        parameters.skill_set.optional_skills
    )
    context = f"Project scheduling for {parameters.employee_count} employees over {parameters.days_in_schedule} days"

    logging.info(f"Starting workflow with timeout: {AGENTS_CONFIG.workflow_timeout}s")
    logging.info(f"Input length: {len(input_str)} characters")
    logging.info(f"Available skills: {available_skills}")

    try:
        agent_output = await agent.run_workflow(
            query=input_str, skills=available_skills, context=context
        )
        logging.info(
            f"Workflow completed successfully. Generated {len(agent_output)} tasks."
        )
        return agent_output
    except Exception as e:
        logging.error(f"Workflow failed: {e}")
        raise
