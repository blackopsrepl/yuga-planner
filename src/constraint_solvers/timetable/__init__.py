"""
Timetable constraint solver module.

This module contains the domain models, constraints, and solver logic
for employee scheduling optimization.
"""

try:
    from .domain import (
        Employee,
        Task,
        EmployeeSchedule,
        ScheduleInfo,
    )
    from .solver import solver_manager, solution_manager
    from .constraints import (
        get_slot_overlap,
        get_slot_date,
        tasks_violate_sequence_order,
        define_constraints,
    )

    _TIMEFOLD_AVAILABLE = True
except ImportError as e:
    # Handle missing timefold dependency gracefully
    _TIMEFOLD_AVAILABLE = False
    Employee = None
    Task = None
    EmployeeSchedule = None
    ScheduleInfo = None
    solver_manager = None
    solution_manager = None
    get_slot_overlap = None
    get_slot_date = None
    tasks_violate_sequence_order = None
    define_constraints = None

__all__ = [
    # Domain models
    "Employee",
    "Task",
    "EmployeeSchedule",
    "ScheduleInfo",
    # Solver managers
    "solver_manager",
    "solution_manager",
    # Constraint functions
    "get_slot_overlap",
    "get_slot_date",
    "tasks_violate_sequence_order",
    "define_constraints",
]
