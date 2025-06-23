import icalendar
import sys
from pathlib import Path

# Import standardized test utilities
from tests.test_utils import get_test_logger, create_test_results

# Initialize standardized test logger
logger = get_test_logger(__name__)


def test_calendar_operations():
    """Test basic calendar operations and parsing"""

    logger.start_test("Testing calendar operations and parsing")

    ics_path = Path("tests/data/calendar.ics")

    # Verify test data exists
    assert ics_path.exists(), f"Test calendar file not found: {ics_path}"
    logger.debug(f"Reading calendar from: {ics_path}")

    calendar = icalendar.Calendar.from_ical(ics_path.read_bytes())

    def to_iso(val):
        if hasattr(val, "dt"):
            dt = val.dt
            if hasattr(dt, "isoformat"):
                return dt.isoformat()
            return str(dt)
        return str(val)

    event_count = 0

    for event in calendar.events:
        event_count += 1
        summary = event.get("summary")
        start_time = to_iso(event.get("dtstart"))
        end_time = to_iso(event.get("dtend"))

        logger.debug(f"Event {event_count}: {summary}")
        logger.debug(f"  Start: {start_time}")
        logger.debug(f"  End: {end_time}")

        # Basic validation
        assert summary is not None, f"Event {event_count} should have a summary"
        assert start_time is not None, f"Event {event_count} should have a start time"

    logger.info(f"✅ Successfully parsed {event_count} calendar events")

    # Verify we found some events
    assert event_count > 0, "Calendar should contain at least one event"

    logger.pass_test(
        f"Calendar operations work correctly - parsed {event_count} events"
    )


if __name__ == "__main__":
    logger.section("Calendar Operations Tests")

    # Create test results tracker
    results = create_test_results(logger)

    # Run the test
    results.run_test("calendar_operations", test_calendar_operations)

    # Generate summary and exit with appropriate code
    all_passed = results.summary()
    sys.exit(0 if all_passed else 1)
