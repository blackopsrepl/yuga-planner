from typing import Dict
from constraint_solvers.timetable.domain import EmployeeSchedule


class AppState:
    """Central state management for the Yuga Planner application."""

    def __init__(self):
        self._solved_schedules: Dict[str, EmployeeSchedule] = {}

    @property
    def solved_schedules(self) -> Dict[str, EmployeeSchedule]:
        """Get the solved schedules dictionary."""
        return self._solved_schedules

    def add_solved_schedule(self, key: str, schedule: EmployeeSchedule) -> None:
        """Add a solved schedule to the state."""
        self._solved_schedules[key] = schedule

    def get_solved_schedule(self, key: str) -> EmployeeSchedule | None:
        """Get a specific solved schedule by key."""
        return self._solved_schedules.get(key)

    def clear_solved_schedules(self) -> None:
        """Clear all solved schedules."""
        self._solved_schedules.clear()

    def has_solved_schedule(self, key: str) -> bool:
        """Check if a solved schedule exists for the given key."""
        return key in self._solved_schedules


# Global app state instance
app_state = AppState()
