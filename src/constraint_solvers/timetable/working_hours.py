# =========================
#     WORKING HOURS CONFIG
# =========================

# Working hours: 9:00-13:00 (8 slots) + 14:00-18:00 (8 slots) = 16 slots per working day
SLOTS_PER_WORKING_DAY = 16
MORNING_SLOTS = 8  # 9:00-13:00 (4 hours * 2 slots/hour)
AFTERNOON_SLOTS = 8  # 14:00-18:00 (4 hours * 2 slots/hour)


def get_working_day_from_slot(slot: int) -> int:
    """Get the working day index (0=first working day) from a slot.

    Args:
        slot (int): The slot index.

    Returns:
        int: The working day index (0-based).
    """
    return slot // SLOTS_PER_WORKING_DAY


def get_slot_within_day(slot: int) -> int:
    """Get the slot position within a working day (0-15).

    Args:
        slot (int): The slot index.

    Returns:
        int: The slot position within the day (0-15).
    """
    return slot % SLOTS_PER_WORKING_DAY


def task_spans_lunch_break(task) -> bool:
    """Check if a task spans across the lunch break period.

    Args:
        task: The task to check.

    Returns:
        bool: True if the task spans across lunch break.
    """
    start_slot_in_day = get_slot_within_day(task.start_slot)
    end_slot_in_day = start_slot_in_day + task.duration_slots - 1

    # If task starts in morning (0-7) and ends in afternoon (8-15), it spans lunch
    return start_slot_in_day < MORNING_SLOTS and end_slot_in_day >= MORNING_SLOTS
