from datetime import datetime, timedelta
import pandas as pd


def schedule_to_dataframe(schedule) -> pd.DataFrame:
    """
    Convert an EmployeeSchedule to a pandas DataFrame.

    Args:
        schedule (EmployeeSchedule): The schedule to convert.

    Returns:
        pd.DataFrame: The converted DataFrame.
    """
    data: list[dict[str, str]] = []

    # Process each task in the schedule
    for task in schedule.tasks:
        # Get employee name or "Unassigned" if no employee assigned
        employee: str = task.employee.name if task.employee else "Unassigned"

        # Calculate start and end times based on 30-minute slots
        start_time: datetime = datetime.now() + timedelta(minutes=30 * task.start_slot)
        end_time: datetime = start_time + timedelta(minutes=30 * task.duration_slots)

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
    data: list[dict[str, str]] = []

    for emp in schedule.employees:
        first, last = emp.name.split(" ", 1) if " " in emp.name else (emp.name, "")
        data.append(
            {
                "First Name": first,
                "Last Name": last,
                "Skills": ", ".join(sorted(emp.skills)),
            }
        )

    return pd.DataFrame(data)
