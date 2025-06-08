from timefold.solver import SolverStatus
from timefold.solver.domain import *
from timefold.solver.score import HardSoftDecimalScore
from datetime import datetime, date
from typing import Annotated
from dataclasses import dataclass, field


@dataclass
class Employee:
    name: Annotated[str, PlanningId]
    skills: Annotated[set[str], field(default_factory=set)]
    unavailable_dates: Annotated[set[date], field(default_factory=set)] = field(
        default_factory=set
    )
    undesired_dates: Annotated[set[date], field(default_factory=set)] = field(
        default_factory=set
    )
    desired_dates: Annotated[set[date], field(default_factory=set)] = field(
        default_factory=set
    )


@planning_entity
@dataclass
class Task:
    id: Annotated[str, PlanningId]
    description: str
    duration_slots: int  # Number of 30-minute slots required
    start_slot: Annotated[
        int, PlanningVariable(value_range_provider_refs=["startSlotRange"])
    ]  # Slot index when the task starts
    required_skill: str
    employee: Annotated[
        Employee | None, PlanningVariable(value_range_provider_refs=["employeeRange"])
    ] = None


@dataclass
class ScheduleInfo:
    total_slots: int  # Total number of 30-minute slots in the schedule


@planning_solution
@dataclass
class EmployeeSchedule:
    employees: Annotated[
        list[Employee],
        ProblemFactCollectionProperty,
        ValueRangeProvider(id="employeeRange"),
    ]
    tasks: Annotated[list[Task], PlanningEntityCollectionProperty]
    schedule_info: Annotated[ScheduleInfo, ProblemFactProperty]
    score: Annotated[HardSoftDecimalScore | None, PlanningScore] = None
    solver_status: SolverStatus | None = None

    def get_start_slot_range(
        self,
    ) -> Annotated[list[int], ValueRangeProvider(id="startSlotRange")]:
        """Returns all possible start slots."""
        return list(range(self.schedule_info.total_slots))
