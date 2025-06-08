from datetime import date, timedelta
from itertools import product

from random import Random
from dataclasses import dataclass, field

from constraint_solvers.timetable.domain import *


# =========================
#        CONSTANTS
# =========================

# Each slot is 30 minutes
SLOTS_PER_DAY = 16

### TASKS ###
DEMO_TASKS = [
    ("Install Operating System", 3),
    ("Configure Network", 2),
    ("Setup Database", 4),
    ("Install Software", 2),
    ("System Testing", 3),
    ("User Training", 4),
    ("Documentation", 2),
    ("Security Audit", 3),
    ("Performance Tuning", 4),
    ("Backup Setup", 2),
]

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


@dataclass(kw_only=True)
class DemoDataParameters:
    required_skills: tuple[str, ...]
    optional_skills: tuple[str, ...]
    days_in_schedule: int
    employee_count: int
    optional_skill_distribution: tuple[CountDistribution, ...]
    availability_count_distribution: tuple[CountDistribution, ...]
    random_seed: int = field(default=37)


# =========================
#        DEMO PARAMS
# =========================
LARGE_DEMO_PARAMS = DemoDataParameters(
    required_skills=("System Admin", "Network Engineer"),
    optional_skills=("Security Expert", "Database Admin", "DevOps Engineer"),
    days_in_schedule=28,
    employee_count=50,
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


def generate_demo_data() -> EmployeeSchedule:
    """
    Generates demo employee schedule data using the LARGE demo parameters.

    TODO: allow to choose data from TaskComposerAgent
    """
    parameters: DemoDataParameters = LARGE_DEMO_PARAMS
    start_date: date = earliest_monday_on_or_after(date.today())
    random: Random = Random(parameters.random_seed)
    employees: list[Employee] = generate_employees(parameters, random)
    tasks: list[Task] = []
    total_slots: int = parameters.days_in_schedule * SLOTS_PER_DAY

    tasks = generate_tasks(parameters, random)

    generate_employee_availability(employees, parameters, start_date, random)

    return EmployeeSchedule(
        employees=employees,
        tasks=tasks,
        schedule_info=ScheduleInfo(total_slots=total_slots),
    )


def generate_employees(
    parameters: DemoDataParameters, random: Random
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
        skills = []
        skills += random.sample(parameters.optional_skills, count)
        skills += random.sample(parameters.required_skills, 1)
        employees.append(Employee(name=name_permutations[i], skills=set(skills)))
    return employees


def generate_employee_availability(
    employees: list[Employee],
    parameters: DemoDataParameters,
    start_date: date,
    random: Random,
) -> None:
    """
    Sets up random availability preferences for employees across the schedule period.
    For each day, randomly selects a number of employees and assigns them random
    availability preferences (unavailable, undesired, or desired).
    """
    for i in range(parameters.days_in_schedule):
        (count,) = random.choices(
            population=counts(parameters.availability_count_distribution),
            weights=weights(parameters.availability_count_distribution),
        )
        employees_with_availabilities_on_day = random.sample(employees, count)
        current_date = start_date + timedelta(days=i)
        for employee in employees_with_availabilities_on_day:
            rand_num = random.randint(0, 2)
            if rand_num == 0:
                employee.unavailable_dates.add(current_date)
            elif rand_num == 1:
                employee.undesired_dates.add(current_date)
            elif rand_num == 2:
                employee.desired_dates.add(current_date)


def generate_tasks(parameters: DemoDataParameters, random: Random) -> list[Task]:
    """
    Generates a list of Task objects with random descriptions and durations.
    """
    tasks: list[Task] = []

    ids = generate_task_ids()

    # Create tasks
    for description, duration in DEMO_TASKS:
        if random.random() >= 0.5:
            required_skill = random.choice(parameters.required_skills)
        else:
            required_skill = random.choice(parameters.optional_skills)
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
