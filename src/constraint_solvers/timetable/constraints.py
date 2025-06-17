### GENERAL IMPORTS ###
from datetime import date, timedelta

### DOMAIN ###
from .domain import Employee, Task, ScheduleInfo

### TIMEFOLD ###
from timefold.solver.score import HardSoftDecimalScore
from timefold.solver.score._constraint_factory import ConstraintFactory
from timefold.solver.score._joiners import Joiners
from timefold.solver.score._group_by import ConstraintCollectors
from timefold.solver.score._annotations import constraint_provider


def get_slot_overlap(task1: Task, task2: Task) -> int:
    """Calculate the number of overlapping slots between two tasks.

    Args:
        task1 (Task): The first task.
        task2 (Task): The second task.

    Returns:
        int: The number of overlapping slots.
    """
    task1_end: int = task1.start_slot + task1.duration_slots
    task2_end: int = task2.start_slot + task2.duration_slots
    overlap_start: int = max(task1.start_slot, task2.start_slot)
    overlap_end: int = min(task1_end, task2_end)
    return max(0, overlap_end - overlap_start)


def get_slot_date(slot: int) -> date:
    """Convert a slot index to a date.

    Args:
        slot (int): The slot index.

    Returns:
        date: The date corresponding to the slot.
    """
    return date.today() + timedelta(days=slot // 20)  # 20 slots per day


def tasks_violate_sequence_order(task1: Task, task2: Task) -> bool:
    """Check if two tasks violate the project sequence order.

    Args:
        task1 (Task): The first task.
        task2 (Task): The second task.

    Returns:
        bool: True if task1 should come before task2 but overlaps with it.
    """
    # Different tasks only
    if task1.id == task2.id:
        return False

    # Both tasks must have project_id attribute
    if not (hasattr(task1, "project_id") and hasattr(task2, "project_id")):
        return False

    # Task1 must belong to a project
    if task1.project_id == "":
        return False

    # Tasks must be in the same project
    if task1.project_id != task2.project_id:
        return False

    # Task1 must have lower sequence number (should come first)
    if task1.sequence_number >= task2.sequence_number:
        return False

    # Task1 overlaps with task2 (task1 should finish before task2 starts)
    return task1.start_slot + task1.duration_slots > task2.start_slot


@constraint_provider
def define_constraints(constraint_factory: ConstraintFactory) -> list:
    """
    Define the constraints for the timetable problem.

    Args:
        constraint_factory (ConstraintFactory): The constraint factory.

    Returns:
        list[Constraint]: The constraints.
    """
    return [
        # Hard constraints
        required_skill(constraint_factory),
        no_overlapping_tasks(constraint_factory),
        task_within_schedule(constraint_factory),
        task_fits_in_schedule(constraint_factory),
        unavailable_employee(constraint_factory),
        maintain_project_task_order(constraint_factory),
        # Soft constraints
        undesired_day_for_employee(constraint_factory),
        desired_day_for_employee(constraint_factory),
        balance_employee_task_assignments(constraint_factory),
    ]


### CONSTRAINTS ###
def required_skill(constraint_factory: ConstraintFactory):
    return (
        constraint_factory.for_each(Task)
        .filter(
            lambda task: task.employee is not None
            and task.required_skill not in task.employee.skills
        )
        .penalize(HardSoftDecimalScore.ONE_HARD)
        .as_constraint("Required skill")
    )


def no_overlapping_tasks(constraint_factory: ConstraintFactory):
    return (
        constraint_factory.for_each_unique_pair(
            Task,
            Joiners.equal(lambda task: task.employee.name),
            Joiners.overlapping(
                lambda task: task.start_slot,
                lambda task: task.start_slot + task.duration_slots,
            ),
        )
        .penalize(HardSoftDecimalScore.ONE_HARD, get_slot_overlap)
        .as_constraint("No overlapping tasks")
    )


def task_within_schedule(constraint_factory: ConstraintFactory):
    return (
        constraint_factory.for_each(Task)
        .filter(lambda task: task.start_slot < 0)
        .penalize(HardSoftDecimalScore.ONE_HARD)
        .as_constraint("Task within schedule")
    )


def task_fits_in_schedule(constraint_factory: ConstraintFactory):
    return (
        constraint_factory.for_each(Task)
        .join(ScheduleInfo)
        .filter(
            lambda task, schedule_info: task.start_slot + task.duration_slots
            > schedule_info.total_slots
        )
        .penalize(HardSoftDecimalScore.ONE_HARD)
        .as_constraint("Task fits in schedule")
    )


def unavailable_employee(constraint_factory: ConstraintFactory):
    return (
        constraint_factory.for_each(Task)
        .filter(
            lambda task: task.employee is not None
            and get_slot_date(task.start_slot) in task.employee.unavailable_dates
        )
        .penalize(HardSoftDecimalScore.ONE_HARD)
        .as_constraint("Unavailable employee")
    )


def undesired_day_for_employee(constraint_factory: ConstraintFactory):
    return (
        constraint_factory.for_each(Task)
        .filter(
            lambda task: task.employee is not None
            and get_slot_date(task.start_slot) in task.employee.undesired_dates
        )
        .penalize(HardSoftDecimalScore.ONE_SOFT)
        .as_constraint("Undesired day for employee")
    )


def desired_day_for_employee(constraint_factory: ConstraintFactory):
    return (
        constraint_factory.for_each(Task)
        .filter(
            lambda task: task.employee is not None
            and get_slot_date(task.start_slot) in task.employee.desired_dates
        )
        .reward(HardSoftDecimalScore.ONE_SOFT)
        .as_constraint("Desired day for employee")
    )


def maintain_project_task_order(constraint_factory: ConstraintFactory):
    """Ensure tasks within the same project maintain their original order."""
    return (
        constraint_factory.for_each(Task)
        .join(Task)
        .filter(tasks_violate_sequence_order)
        .penalize(
            HardSoftDecimalScore.ONE_SOFT,
            lambda task1, task2: 100
            * (task1.start_slot + task1.duration_slots - task2.start_slot),
        )  # High penalty (100x) proportional to overlap to strongly encourage proper sequencing
        .as_constraint("Project task sequence order")
    )


def balance_employee_task_assignments(constraint_factory: ConstraintFactory):
    return (
        constraint_factory.for_each(Task)
        .group_by(lambda task: task.employee, ConstraintCollectors.count())
        .complement(
            Employee, lambda e: 0
        )  # Include all employees which are not assigned to any task
        .group_by(
            ConstraintCollectors.load_balance(
                lambda employee, task_count: employee,
                lambda employee, task_count: task_count,
            )
        )
        .penalize_decimal(
            HardSoftDecimalScore.ONE_SOFT,
            lambda load_balance: load_balance.unfairness(),
        )
        .as_constraint("Balance employee task assignments")
    )
