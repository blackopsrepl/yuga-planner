from datetime import date, timedelta
from random import Random
from itertools import product

from factory.data_models import *
from constraint_solvers.timetable.domain import *


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


def generate_employees(
    parameters: TimeTableDataParameters,
    random: Random,
    required_skills_needed: set[str] = None,
) -> list[Employee]:
    """
    Generates a list of Employee objects with random names and skills.
    Ensures that collectively the employees have all required_skills_needed.
    """
    name_permutations = [
        f"{first_name} {last_name}"
        for first_name, last_name in product(FIRST_NAMES, LAST_NAMES)
    ]

    random.shuffle(name_permutations)

    employees = []

    # If specific skills are needed, ensure they're covered
    if required_skills_needed:
        skills_needed = set(required_skills_needed)

        # For single employee (MCP case), give them all needed skills plus some random ones
        if parameters.employee_count == 1:
            all_available_skills = list(parameters.skill_set.required_skills) + list(
                parameters.skill_set.optional_skills
            )
            # Give all available skills to the single employee to handle any task
            employees.append(
                Employee(name=name_permutations[0], skills=set(all_available_skills))
            )
            return employees

        # For multiple employees, distribute needed skills and add random skills
        for i in range(parameters.employee_count):
            (count,) = random.choices(
                population=counts(parameters.optional_skill_distribution),
                weights=weights(parameters.optional_skill_distribution),
            )
            count = min(count, len(parameters.skill_set.optional_skills))

            skills = []

            # Ensure each employee gets at least one required skill
            skills += random.sample(parameters.skill_set.required_skills, 1)

            # Add random optional skills
            skills += random.sample(parameters.skill_set.optional_skills, count)

            # If there are still skills needed and this is one of the first employees,
            # ensure they get some of the needed skills
            if skills_needed and i < len(skills_needed):
                needed_skill = skills_needed.pop()
                if needed_skill not in skills:
                    skills.append(needed_skill)

            employees.append(Employee(name=name_permutations[i], skills=set(skills)))

    else:
        # Original random generation when no specific skills are needed
        for i in range(parameters.employee_count):
            (count,) = random.choices(
                population=counts(parameters.optional_skill_distribution),
                weights=weights(parameters.optional_skill_distribution),
            )
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


def generate_employee_availability_mcp(
    employees: list[Employee],
) -> None:
    """
    For MCP data generator: does not set any unavailable, desired, or undesired days for employees.
    All availability sets remain empty.
    """
    for employee in employees:
        employee.unavailable_dates.clear()
        employee.undesired_dates.clear()
        employee.desired_dates.clear()


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


def generate_tasks_from_calendar(
    parameters: TimeTableDataParameters,
    random: Random,
    calendar_entries: list[dict],
) -> list[Task]:
    """
    Given a list of calendar entry dicts, generate Task objects with randomized required_skill.
    Output format matches generate_tasks.
    """
    from datetime import datetime

    tasks: list[Task] = []
    ids = generate_task_ids()

    for entry in calendar_entries:
        try:
            summary = entry.get("summary", "Event")
            dtstart = entry.get("dtstart", "").replace("Z", "+00:00")
            dtend = entry.get("dtend", "").replace("Z", "+00:00")
            start_dt = datetime.fromisoformat(dtstart) if dtstart else None
            end_dt = datetime.fromisoformat(dtend) if dtend else None
            if start_dt and end_dt:
                duration_minutes = int((end_dt - start_dt).total_seconds() // 60)
                duration_slots = max(1, duration_minutes // 30)
            else:
                duration_slots = 2  # Default 1 hour

            # Randomize required_skill as in generate_tasks
            if random.random() >= 0.5:
                required_skill = random.choice(parameters.skill_set.required_skills)

            else:
                required_skill = random.choice(parameters.skill_set.optional_skills)

            tasks.append(
                Task(
                    id=next(ids),
                    description=summary,
                    duration_slots=duration_slots,
                    start_slot=0,  # This will be assigned by the solver
                    required_skill=required_skill,
                )
            )

        except Exception:
            continue

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
    Convert task_composer_agent output (list of (description, duration, skill)) to Task objects.
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
