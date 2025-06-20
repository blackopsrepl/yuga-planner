# =========================
#     WORKING HOURS CONFIG
# =========================

# Working hours: 9:00-18:00 (20 slots) = 20 slots per working day
# Each slot is 30 minutes, starting at 9:00 AM
SLOTS_PER_WORKING_DAY = 20  # 9:00-18:00 (9 hours * 2 slots/hour)
MORNING_SLOTS = 8  # 9:00-13:00 (4 hours * 2 slots/hour)
AFTERNOON_SLOTS = 10  # 14:00-18:00 (4 hours * 2 slots/hour)
LUNCH_BREAK_START_SLOT = 8  # 13:00-14:00
LUNCH_BREAK_END_SLOT = 10  # 14:00

from datetime import datetime, date, time, timezone, timedelta


def slot_to_datetime(slot: int, base_date: date = None, base_timezone=None) -> datetime:
    """
    Convert a slot index to a naive datetime in local time, accounting for working days.

    Args:
        slot: The slot index (each slot = 30 minutes within working hours)
        base_date: Base date for slot 0 (defaults to today)
        base_timezone: Ignored (kept for API compatibility)

    Returns:
        datetime: The corresponding naive datetime in local time
    """
    if base_date is None:
        base_date = date.today()

    # Calculate which working day and slot within that day
    working_day = get_working_day_from_slot(slot)
    slot_within_day = get_slot_within_day(slot)

    # Get the actual calendar date for this working day
    target_date = base_date + timedelta(days=working_day)

    # Calculate time within the working day (9:00 AM + slot_within_day * 30 minutes)
    minutes_from_9am = slot_within_day * 30
    target_time = datetime.combine(
        target_date, datetime.min.time().replace(hour=9)
    ) + timedelta(minutes=minutes_from_9am)

    return target_time


def get_working_day_from_slot(slot: int) -> int:
    """Get the working day index (0=first working day) from a slot.

    Args:
        slot (int): The slot index.

    Returns:
        int: The working day index (0-based).
    """
    return slot // SLOTS_PER_WORKING_DAY


def get_slot_within_day(slot: int) -> int:
    """Get the slot position within a working day (0-19).

    Args:
        slot (int): The slot index.

    Returns:
        int: The slot position within the day (0-19).
    """
    return slot % SLOTS_PER_WORKING_DAY


def task_spans_lunch_break(task) -> bool:
    """Check if a task spans across the lunch break period (13:00-14:00).

    Args:
        task: The task to check.

    Returns:
        bool: True if the task spans across lunch break.
    """
    start_slot_in_day = get_slot_within_day(task.start_slot)
    end_slot_in_day = start_slot_in_day + task.duration_slots - 1

    # Check if task overlaps with lunch break slots (8-9, which is 13:00-14:00)
    return (
        start_slot_in_day <= LUNCH_BREAK_END_SLOT - 1
        and end_slot_in_day >= LUNCH_BREAK_START_SLOT
    )


def is_weekend_slot(slot: int) -> bool:
    """Check if a slot falls on a weekend.

    Args:
        slot: The slot index

    Returns:
        bool: True if the slot is on a weekend
    """
    working_day = get_working_day_from_slot(slot)
    # For simplicity, assume every 7th day starting from day 5 and 6 are weekends
    # This is a simplification - in practice you'd want to use actual calendar logic
    day_of_week = working_day % 7
    return day_of_week >= 5  # Saturday (5) and Sunday (6)


def get_slot_date(slot: int, base_date: date = None) -> date:
    """Get the date for a given slot.

    Args:
        slot: The slot index
        base_date: Base date for slot 0 (defaults to today)

    Returns:
        date: The date for this slot
    """
    if base_date is None:
        base_date = date.today()

    working_days = get_working_day_from_slot(slot)
    return base_date + timedelta(days=working_days)
