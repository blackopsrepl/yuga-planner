from icalendar import Calendar


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

                entries.append(
                    {
                        "summary": summary,
                        "dtstart": to_iso(dtstart),
                        "dtend": to_iso(dtend),
                    }
                )
        return entries, None
    except Exception as e:
        return None, str(e)
