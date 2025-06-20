from icalendar import Calendar
from datetime import datetime, date, timezone, timedelta
from typing import Optional, Tuple, List, Dict, Any
from constraint_solvers.timetable.working_hours import (
    SLOTS_PER_WORKING_DAY,
    MORNING_SLOTS,
)


def extract_ical_entries(file_bytes):
    try:
        cal = Calendar.from_ical(file_bytes)
        entries = []

        for component in cal.walk():
            if component.name == "VEVENT":
                summary = str(component.get("summary", ""))
                dtstart = component.get("dtstart", "")
                dtend = component.get("dtend", "")

                def to_iso(val):
                    if hasattr(val, "dt"):
                        dt = val.dt

                        if hasattr(dt, "isoformat"):
                            return dt.isoformat()

                        return str(dt)

                    return str(val)

                def to_datetime(val):
                    """Convert icalendar datetime to Python datetime object, normalized to current timezone."""
                    if hasattr(val, "dt"):
                        dt = val.dt
                        if isinstance(dt, datetime):
                            # If timezone-aware, convert to current timezone, then make naive
                            if dt.tzinfo is not None:
                                # Convert to local timezone then strip timezone info
                                local_dt = dt.astimezone()
                                return local_dt.replace(tzinfo=None)
                            else:
                                # Already naive, return as-is
                                return dt
                        elif isinstance(dt, date):
                            # Convert date to datetime at 9 AM (naive)
                            return datetime.combine(
                                dt, datetime.min.time().replace(hour=9)
                            )
                    return None

                # Parse datetime objects for slot calculation (now normalized to current timezone)
                start_datetime = to_datetime(dtstart)
                end_datetime = to_datetime(dtend)

                entry = {
                    "summary": summary,
                    "dtstart": to_iso(dtstart),
                    "dtend": to_iso(dtend),
                }

                # Add datetime objects for slot calculation
                if start_datetime:
                    entry["start_datetime"] = start_datetime
                if end_datetime:
                    entry["end_datetime"] = end_datetime

                entries.append(entry)

        return entries, None

    except Exception as e:
        return None, str(e)


def get_earliest_calendar_date(
    calendar_entries: List[Dict[str, Any]]
) -> Optional[date]:
    """
    Find the earliest date from calendar entries to use as base_date for scheduling.

    Args:
        calendar_entries: List of calendar entry dictionaries

    Returns:
        The earliest date found, or None if no valid dates found
    """
    earliest_date = None

    for entry in calendar_entries:
        start_datetime = entry.get("start_datetime")
        if start_datetime and isinstance(start_datetime, datetime):
            entry_date = start_datetime.date()
            if earliest_date is None or entry_date < earliest_date:
                earliest_date = entry_date

    return earliest_date


def validate_calendar_working_hours(
    calendar_entries: List[Dict[str, Any]]
) -> Tuple[bool, str]:
    """
    Validate that all calendar entries fall within standard working hours (9:00-18:00) and don't span lunch break (13:00-14:00).

    Args:
        calendar_entries: List of calendar entry dictionaries

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not calendar_entries:
        return True, ""

    violations = []

    for entry in calendar_entries:
        summary = entry.get("summary", "Unknown Event")
        start_datetime = entry.get("start_datetime")
        end_datetime = entry.get("end_datetime")

        if start_datetime and isinstance(start_datetime, datetime):
            if start_datetime.hour < 9:
                violations.append(
                    f"'{summary}' starts at {start_datetime.hour:02d}:{start_datetime.minute:02d} (before 9:00)"
                )

        if end_datetime and isinstance(end_datetime, datetime):
            if end_datetime.hour > 18 or (
                end_datetime.hour == 18 and end_datetime.minute > 0
            ):
                violations.append(
                    f"'{summary}' ends at {end_datetime.hour:02d}:{end_datetime.minute:02d} (after 18:00)"
                )

        # Check for lunch break spanning (13:00-14:00)
        if (
            start_datetime
            and end_datetime
            and isinstance(start_datetime, datetime)
            and isinstance(end_datetime, datetime)
        ):
            start_hour_min = start_datetime.hour + start_datetime.minute / 60.0
            end_hour_min = end_datetime.hour + end_datetime.minute / 60.0

            # Check if task spans across lunch break (13:00-14:00)
            if start_hour_min < 14.0 and end_hour_min > 13.0:
                violations.append(
                    f"'{summary}' ({start_datetime.hour:02d}:{start_datetime.minute:02d}-{end_datetime.hour:02d}:{end_datetime.minute:02d}) spans lunch break (13:00-14:00)"
                )

    if violations:
        error_msg = "Calendar entries violate working constraints:\n" + "\n".join(
            violations
        )
        return False, error_msg

    return True, ""


def datetime_to_slot(dt: datetime, base_date: date) -> int:
    """
    Convert a datetime to a 30-minute slot index within working days.

    Args:
        dt: The datetime to convert (should be naive local time)
        base_date: The base date (slot 0 = base_date at 9:00 AM local time)

    Returns:
        The slot index (each slot = 30 minutes within working hours)
    """
    # Calculate which working day this datetime falls on
    days_from_base = (dt.date() - base_date).days

    # Calculate time within the working day (minutes from 9:00 AM)
    minutes_from_9am = (dt.hour - 9) * 60 + dt.minute

    # Convert to slot within the day (each slot = 30 minutes)
    slot_within_day = round(minutes_from_9am / 30)

    # Calculate total slot index
    total_slot = days_from_base * SLOTS_PER_WORKING_DAY + slot_within_day

    # Ensure non-negative slot
    return max(0, total_slot)


def calculate_duration_slots(start_dt: datetime, end_dt: datetime) -> int:
    """
    Calculate duration in 30-minute slots between two datetimes (naive local time).

    Args:
        start_dt: Start datetime (naive local time)
        end_dt: End datetime (naive local time)

    Returns:
        Duration in 30-minute slots (minimum 1 slot)
    """
    # Calculate difference in minutes (both should be naive local time)
    time_diff = end_dt - start_dt
    total_minutes = time_diff.total_seconds() / 60

    # Convert to 30-minute slots, rounding up to ensure task duration is preserved
    duration_slots = max(1, round(total_minutes / 30))

    return duration_slots
