import os, json
import gradio as gr

from datetime import date, timedelta
from itertools import product
from random import Random
from dataclasses import dataclass, field

from agents.TaskComposerAgent import TaskComposerAgent
from domain import AgentsConfig, AGENTS_CONFIG

from constraint_solvers.timetable.domain import *

import logging

logging.basicConfig(level=logging.INFO)

# =========================
#        CONSTANTS
# =========================

# Each slot is 30 minutes - 20 slots = 10 hours working day
SLOTS_PER_DAY = 20

### EMPLOYEES ###
FIRST_NAMES = ("Amy", "Beth", "Carl", "Dan", "Elsa", "Flo", "Gus", "Hugo", "Ivy", "Jay")
LAST_NAMES = (
    "Cole",
    "Fox",
    "Green",
    "Jones",
    "King",
    "Li",
    "Poe",
    "Rye",
    "Smith",
    "Watt",
)

# =========================
#        DATA MODELS
# =========================
@dataclass(frozen=True, kw_only=True)
class CountDistribution:
    count: int
    weight: float


@dataclass(frozen=True, kw_only=True)
class SkillSet:
    required_skills: tuple[str, ...]
    optional_skills: tuple[str, ...]


@dataclass(kw_only=True)
class TimeTableDataParameters:
    skill_set: SkillSet
    days_in_schedule: int
    employee_count: int
    optional_skill_distribution: tuple[CountDistribution, ...]
    availability_count_distribution: tuple[CountDistribution, ...]
    random_seed: int = field(default=37)


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

# =========================
#        AGENT DATA
# =========================
async def generate_agent_data(
    file, project_id: str = "", employee_count: int = None, days_in_schedule: int = None
) -> EmployeeSchedule:
    """
    Generates an EmployeeSchedule using tasks from TaskComposerAgent output.
    """
    parameters: TimeTableDataParameters = DATA_PARAMS

    # Override parameters if provided
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

    # Read file
    # Debug info - only log in debug mode
    import os

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

    # Run agent with skills and context
    agent = TaskComposerAgent(AGENTS_CONFIG)  # Use global config

    # Get available skills from parameters
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
    except Exception as e:
        logging.error(f"Workflow failed: {e}")
        raise

    tasks = tasks_from_agent_output(agent_output, parameters, project_id)
    generate_employee_availability(employees, parameters, start_date, randomizer)

    return EmployeeSchedule(
        employees=employees,
        tasks=tasks,
        schedule_info=ScheduleInfo(total_slots=total_slots),
    )


def generate_employees(
    parameters: TimeTableDataParameters, random: Random
) -> list[Employee]:
    """
    Generates a list of Employee objects with random names and skills.
    """
    name_permutations = [
        f"{first_name} {last_name}"
        for first_name, last_name in product(FIRST_NAMES, LAST_NAMES)
    ]

    random.shuffle(name_permutations)

    employees = []
    for i in range(parameters.employee_count):
        (count,) = random.choices(
            population=counts(parameters.optional_skill_distribution),
            weights=weights(parameters.optional_skill_distribution),
        )

        # Ensure we don't try to sample more skills than available
        count = min(count, len(parameters.skill_set.optional_skills))

        skills = []
        skills += random.sample(parameters.skill_set.optional_skills, count)
        skills += random.sample(parameters.skill_set.required_skills, 1)
        employees.append(Employee(name=name_permutations[i], skills=set(skills)))

    return employees


def generate_employee_availability(
    employees: list[Employee],
    parameters: TimeTableDataParameters,
    start_date: date,
    random: Random,
) -> None:
    """
    Sets up random availability preferences for employees proportional to schedule length.

    For 365 days:
    - Max 21 unavailable days per employee
    - Max 0-12 undesired days per employee
    - Desired dates remain flexible (0-12 days)

    Scales proportionally for different schedule lengths.
    """
    days_in_schedule = parameters.days_in_schedule

    # Calculate proportional limits based on 365-day baseline
    max_unavailable_per_employee = round((21 / 365) * days_in_schedule)
    max_undesired_per_employee = round((12 / 365) * days_in_schedule)
    max_desired_per_employee = round((12 / 365) * days_in_schedule)

    # Ensure minimum reasonable values
    max_unavailable_per_employee = max(1, max_unavailable_per_employee)
    max_undesired_per_employee = max(0, max_undesired_per_employee)
    max_desired_per_employee = max(0, max_desired_per_employee)

    # Generate all possible dates in the schedule
    all_dates = [start_date + timedelta(days=i) for i in range(days_in_schedule)]

    for employee in employees:
        # Randomly assign unavailable dates (1 to max_unavailable_per_employee)
        num_unavailable = random.randint(1, max_unavailable_per_employee)
        unavailable_dates = random.sample(
            all_dates, min(num_unavailable, len(all_dates))
        )
        employee.unavailable_dates.update(unavailable_dates)

        # Remove unavailable dates from remaining pool for other preferences
        remaining_dates = [d for d in all_dates if d not in employee.unavailable_dates]

        # Randomly assign undesired dates (0 to max_undesired_per_employee)
        if max_undesired_per_employee > 0 and remaining_dates:
            num_undesired = random.randint(
                0, min(max_undesired_per_employee, len(remaining_dates))
            )
            if num_undesired > 0:
                undesired_dates = random.sample(remaining_dates, num_undesired)
                employee.undesired_dates.update(undesired_dates)
                remaining_dates = [
                    d for d in remaining_dates if d not in employee.undesired_dates
                ]

        # Randomly assign desired dates (0 to max_desired_per_employee)
        if max_desired_per_employee > 0 and remaining_dates:
            num_desired = random.randint(
                0, min(max_desired_per_employee, len(remaining_dates))
            )
            if num_desired > 0:
                desired_dates = random.sample(remaining_dates, num_desired)
                employee.desired_dates.update(desired_dates)


def generate_tasks(
    parameters: TimeTableDataParameters,
    random: Random,
    task_tuples: list[tuple[str, int]],
) -> list[Task]:
    """
    Given a list of (description, duration) tuples, generate Task objects with randomized required_skill.
    """
    tasks: list[Task] = []

    ids = generate_task_ids()

    for description, duration in task_tuples:
        if random.random() >= 0.5:
            required_skill = random.choice(parameters.skill_set.required_skills)
        else:
            required_skill = random.choice(parameters.skill_set.optional_skills)
        tasks.append(
            Task(
                id=next(ids),
                description=description,
                duration_slots=duration,
                start_slot=0,  # This will be assigned by the solver
                required_skill=required_skill,
            )
        )
    return tasks


def generate_task_ids():
    current_id = 0
    while True:
        yield str(current_id)
        current_id += 1


# =========================
#     UTILITY FUNCTIONS
# =========================
def counts(distributions: tuple[CountDistribution, ...]) -> tuple[int, ...]:
    """
    Extracts the count values from a tuple of CountDistribution objects.
    """
    return tuple(distribution.count for distribution in distributions)


def weights(distributions: tuple[CountDistribution, ...]) -> tuple[float, ...]:
    """
    Extracts the weight values from a tuple of CountDistribution objects.
    """
    return tuple(distribution.weight for distribution in distributions)


def earliest_monday_on_or_after(target_date: date) -> date:
    """
    Returns the date of the next Monday on or after the given date.
    If the date is already Monday, returns the same date.
    """
    days = (7 - target_date.weekday()) % 7
    return target_date + timedelta(days=days)


def tasks_from_agent_output(agent_output, parameters, project_id: str = ""):
    """
    Convert TaskComposerAgent output (list of (description, duration, skill)) to Task objects.
    """
    from constraint_solvers.timetable.domain import Task

    ids = generate_task_ids()
    tasks = []

    for sequence_num, task_data in enumerate(agent_output):
        # Handle both old format (description, duration) and new format (description, duration, skill)
        if len(task_data) == 3:
            description, duration, required_skill = task_data
        elif len(task_data) == 2:
            description, duration = task_data
            # Fallback to random assignment if no skill provided
            import random

            if random.random() >= 0.5:
                required_skill = random.choice(parameters.skill_set.required_skills)
            else:
                required_skill = random.choice(parameters.skill_set.optional_skills)
        else:
            continue  # skip invalid task data

        try:
            duration_int = int(duration)
        except (ValueError, TypeError):
            continue  # skip this task if duration is invalid

        # Clean up skill name (remove any extra formatting)
        if required_skill:
            required_skill = required_skill.strip()
            # Ensure the skill exists in our skill set
            all_skills = list(parameters.skill_set.required_skills) + list(
                parameters.skill_set.optional_skills
            )
            if required_skill not in all_skills:
                # If skill doesn't match exactly, try to find closest match or fallback to random
                import random

                required_skill = random.choice(parameters.skill_set.required_skills)

        tasks.append(
            Task(
                id=next(ids),
                description=description,
                duration_slots=duration_int,
                start_slot=0,
                required_skill=required_skill,
                project_id=project_id,
                sequence_number=sequence_num,
            )
        )
    return tasks


def skills_from_parameters(parameters: TimeTableDataParameters) -> list[str]:
    return list(parameters.skill_set.required_skills) + list(
        parameters.skill_set.optional_skills
    )
