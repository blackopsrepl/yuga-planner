from datetime import datetime, timedelta, date
import pandas as pd

from factory.data.generators import earliest_monday_on_or_after
from constraint_solvers.timetable.working_hours import (
    SLOTS_PER_WORKING_DAY,
    MORNING_SLOTS,
    slot_to_datetime,
)


def schedule_to_dataframe(schedule) -> pd.DataFrame:
    """
    Convert an EmployeeSchedule to a pandas DataFrame.

    Args:
        schedule (EmployeeSchedule): The schedule to convert.

    Returns:
        pd.DataFrame: The converted DataFrame.
    """
    data: list[dict[str, str]] = []

    # Get base date from schedule info if available
    base_date = None
    if hasattr(schedule, "schedule_info"):
        if hasattr(schedule.schedule_info, "base_date"):
            base_date = schedule.schedule_info.base_date

    # Process each task in the schedule
    for task in schedule.tasks:
        # Get employee name or "Unassigned" if no employee assigned
        employee: str = task.employee.name if task.employee else "Unassigned"

        # Calculate start and end times (naive local time)
        start_time: datetime = slot_to_datetime(task.start_slot, base_date)
        end_time: datetime = slot_to_datetime(
            task.start_slot + task.duration_slots, base_date
        )

        # Add task data to list with availability flags
        data.append(
            {
                "Project": getattr(task, "project_id", ""),
                "Sequence": getattr(task, "sequence_number", 0),
                "Employee": employee,
                "Task": task.description,
                "Start": start_time,
                "End": end_time,
                "Duration (hours)": task.duration_slots / 2,  # Convert slots to hours
                "Required Skill": task.required_skill,
                "Pinned": getattr(task, "pinned", False),  # Include pinned status
                # Check if task falls on employee's unavailable date
                "Unavailable": employee != "Unassigned"
                and hasattr(task.employee, "unavailable_dates")
                and start_time.date() in task.employee.unavailable_dates,
                # Check if task falls on employee's undesired date
                "Undesired": employee != "Unassigned"
                and hasattr(task.employee, "undesired_dates")
                and start_time.date() in task.employee.undesired_dates,
                # Check if task falls on employee's desired date
                "Desired": employee != "Unassigned"
                and hasattr(task.employee, "desired_dates")
                and start_time.date() in task.employee.desired_dates,
            }
        )

    return pd.DataFrame(data)


def employees_to_dataframe(schedule) -> pd.DataFrame:
    """
    Convert an EmployeeSchedule to a pandas DataFrame.

    Args:
        schedule (EmployeeSchedule): The schedule to convert.
    """

    def format_dates(dates_list, max_display=3):
        """Helper function to format dates for display"""
        if not dates_list:
            return "None"
        try:
            sorted_dates = sorted(dates_list)
            if len(sorted_dates) <= max_display:
                return ", ".join(d.strftime("%m/%d") for d in sorted_dates)
            else:
                displayed = ", ".join(
                    d.strftime("%m/%d") for d in sorted_dates[:max_display]
                )
                return f"{displayed} (+{len(sorted_dates) - max_display} more)"
        except Exception:
            return f"{len(dates_list)} dates"

    data: list[dict[str, str]] = []

    for emp in schedule.employees:
        try:
            first, last = emp.name.split(" ", 1) if " " in emp.name else (emp.name, "")

            # Safely get preference dates with fallback to empty sets
            unavailable_dates = getattr(emp, "unavailable_dates", set())
            undesired_dates = getattr(emp, "undesired_dates", set())
            desired_dates = getattr(emp, "desired_dates", set())

            data.append(
                {
                    "First Name": first,
                    "Last Name": last,
                    "Skills": ", ".join(sorted(emp.skills)),
                    "Unavailable Dates": format_dates(unavailable_dates),
                    "Undesired Dates": format_dates(undesired_dates),
                    "Desired Dates": format_dates(desired_dates),
                    "Total Preferences": f"{len(unavailable_dates)} unavailable, {len(undesired_dates)} undesired, {len(desired_dates)} desired",
                }
            )
        except Exception as e:
            # Fallback for any employee that causes issues
            data.append(
                {
                    "First Name": str(emp.name),
                    "Last Name": "",
                    "Skills": ", ".join(sorted(getattr(emp, "skills", []))),
                    "Unavailable Dates": "Error loading",
                    "Undesired Dates": "Error loading",
                    "Desired Dates": "Error loading",
                    "Total Preferences": "Error loading preferences",
                }
            )

    return pd.DataFrame(data)
