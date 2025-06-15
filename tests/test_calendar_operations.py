import icalendar

from pathlib import Path


def test_calendar_operations():
    ics_path = Path("tests/data/calendar.ics")

    calendar = icalendar.Calendar.from_ical(ics_path.read_bytes())

    for event in calendar.events:
        print(event.get("summary"))
        print(event.get("dtstart"))
        print(event.get("dtend"))
