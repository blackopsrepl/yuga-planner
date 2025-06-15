import icalendar

from pathlib import Path


def test_calendar_operations():
    ics_path = Path("tests/data/calendar.ics")

    calendar = icalendar.Calendar.from_ical(ics_path.read_bytes())

    for event in calendar.events:
        print(event.get("summary"))

        def to_iso(val):
            if hasattr(val, "dt"):
                dt = val.dt
                if hasattr(dt, "isoformat"):
                    return dt.isoformat()
                return str(dt)
            return str(val)

        print(to_iso(event.get("dtstart")))
        print(to_iso(event.get("dtend")))
