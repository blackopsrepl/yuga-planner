from timefold.solver import SolverStatus
from timefold.solver.domain import *
from timefold.solver.score import HardSoftDecimalScore

from datetime import date, timezone
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

    def to_dict(self):
        return {
            "name": self.name,
            "skills": list(self.skills),
            "unavailable_dates": [d.isoformat() for d in self.unavailable_dates],
            "undesired_dates": [d.isoformat() for d in self.undesired_dates],
            "desired_dates": [d.isoformat() for d in self.desired_dates],
        }

    @staticmethod
    def from_dict(d):
        return Employee(
            name=d["name"],
            skills=set(d["skills"]),
            unavailable_dates=set(
                date.fromisoformat(s) for s in d["unavailable_dates"]
            ),
            undesired_dates=set(date.fromisoformat(s) for s in d["undesired_dates"]),
            desired_dates=set(date.fromisoformat(s) for s in d["desired_dates"]),
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

    # Identifier for the project this task belongs to (set by the UI when loading multiple project files)
    project_id: str = ""

    # Sequence number within the project to maintain original task order
    sequence_number: int = 0

    # Whether this task is pinned to its current assignment (for calendar events)
    pinned: Annotated[bool, PlanningPin] = False
    employee: Annotated[
        Employee | None, PlanningVariable(value_range_provider_refs=["employeeRange"])
    ] = None

    def to_dict(self):
        return {
            "id": self.id,
            "description": self.description,
            "duration_slots": self.duration_slots,
            "start_slot": self.start_slot,
            "required_skill": self.required_skill,
            "project_id": self.project_id,
            "sequence_number": self.sequence_number,
            "pinned": self.pinned,
            "employee": self.employee.to_dict() if self.employee else None,
        }

    @staticmethod
    def from_dict(d):
        return Task(
            id=d["id"],
            description=d["description"],
            duration_slots=d["duration_slots"],
            start_slot=d["start_slot"],
            required_skill=d["required_skill"],
            project_id=d.get("project_id", ""),
            sequence_number=d.get("sequence_number", 0),
            pinned=d.get("pinned", False),
            employee=Employee.from_dict(d["employee"]) if d["employee"] else None,
        )


@dataclass
class ScheduleInfo:
    total_slots: int  # Total number of 30-minute slots in the schedule
    base_date: date = None  # Base date for slot 0 (optional, defaults to today)
    base_timezone: timezone = None  # Timezone for datetime conversions (optional)

    def to_dict(self):
        return {
            "total_slots": self.total_slots,
            "base_date": self.base_date.isoformat() if self.base_date else None,
            "base_timezone": str(self.base_timezone) if self.base_timezone else None,
        }

    @staticmethod
    def from_dict(d):
        base_date = None
        if d.get("base_date"):
            base_date = date.fromisoformat(d["base_date"])

        base_timezone = None
        if d.get("base_timezone"):
            # Simple timezone parsing - extend as needed
            tz_str = d["base_timezone"]
            if tz_str == "UTC" or "+00:00" in tz_str:
                base_timezone = timezone.utc
            # Add more timezone parsing as needed

        return ScheduleInfo(
            total_slots=d["total_slots"],
            base_date=base_date,
            base_timezone=base_timezone,
        )


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
        """Returns all possible start slots, including slots used by pinned tasks."""
        max_slot = self.schedule_info.total_slots

        # Ensure all pinned task slots are included in the range
        for task in self.tasks:
            if getattr(task, "pinned", False):
                task_end_slot = task.start_slot + task.duration_slots
                if task_end_slot > max_slot:
                    max_slot = task_end_slot

        return list(range(max_slot))

    def to_dict(self):
        return {
            "employees": [e.to_dict() for e in self.employees],
            "tasks": [t.to_dict() for t in self.tasks],
            "schedule_info": self.schedule_info.to_dict(),
            "score": str(self.score) if self.score is not None else None,
            "solver_status": str(self.solver_status)
            if self.solver_status is not None
            else None,
        }

    @staticmethod
    def from_dict(d):
        return EmployeeSchedule(
            employees=[Employee.from_dict(e) for e in d["employees"]],
            tasks=[Task.from_dict(t) for t in d["tasks"]],
            schedule_info=ScheduleInfo.from_dict(d["schedule_info"]),
            # score and solver_status are not restored (not needed for state passing)
        )
