import pytest

from src.utils.load_secrets import load_secrets

# Load environment variables for agent (if needed)
load_secrets("tests/secrets/creds.py")

import factory.data.provider as data_provider
from src.utils.extract_calendar import extract_ical_entries


@pytest.mark.asyncio
async def test_factory_demo_agent():
    # Use a simple string as the project description
    test_input = "Test project for schedule generation."

    # Generate schedule data using generate_agent_data
    schedule = await data_provider.generate_agent_data(test_input)

    # Assert basic schedule properties
    assert len(schedule.employees) > 0
    assert schedule.schedule_info.total_slots > 0
    assert len(schedule.tasks) > 0

    # Verify employee skills
    for employee in schedule.employees:
        assert len(employee.skills) > 0
        # Check that each employee has at least one required skill
        assert any(
            skill in data_provider.SKILL_SET.required_skills
            for skill in employee.skills
        )

    # Verify task properties
    for task in schedule.tasks:
        assert task.duration_slots > 0
        assert task.required_skill
        assert hasattr(task, "project_id")

    # Print schedule details for debugging
    print("Employee names:", [e.name for e in schedule.employees])
    print("Tasks count:", len(schedule.tasks))
    print("Total slots:", schedule.schedule_info.total_slots)


@pytest.mark.asyncio
async def test_factory_mcp():
    # Load the real calendar.ics file
    with open("tests/data/calendar.ics", "rb") as f:
        file_bytes = f.read()
    entries, err = extract_ical_entries(file_bytes)
    assert err is None
    assert entries is not None
    assert len(entries) > 0

    print("\nEntries:")
    print(entries)

    # Use a made-up user message
    user_message = "Create a new AWS VPC."

    # Call generate_mcp_data directly
    df = await data_provider.generate_mcp_data(entries, user_message)

    # Assert the DataFrame is not empty
    assert df is not None
    assert not df.empty

    # Print the DataFrame for debug
    print(df)
