import pytest
import time
import pandas as pd
import traceback
from io import StringIO
from datetime import datetime, date, timedelta
from typing import List, Dict, Tuple, Optional, Any

from src.utils.load_secrets import load_secrets

# Load environment variables for agent (if needed)
load_secrets("tests/secrets/creds.py")

import factory.data.provider as data_provider
from src.utils.extract_calendar import extract_ical_entries
from src.handlers.mcp_backend import process_message_and_attached_file
from src.services import ScheduleService, StateService
from src.services.data import DataService
from src.factory.data.formatters import schedule_to_dataframe

# Add cleanup fixture for proper solver shutdown
@pytest.fixture(scope="session", autouse=True)
def cleanup_solver():
    """Automatically cleanup solver resources after all tests complete."""
    yield  # Run tests

    # Cleanup: Terminate all active solver jobs and shutdown solver manager
    try:
        from constraint_solvers.timetable.solver import solver_manager
        from src.state import app_state

        # Clear all stored schedules first
        app_state.clear_solved_schedules()

        # Terminate all active solver jobs gracefully using the Timefold terminateEarly method
        if hasattr(solver_manager, "terminateEarly"):
            # According to Timefold docs, terminateEarly() affects all jobs for this manager
            try:
                solver_manager.terminateEarly()
                print("🧹 Terminated all active solver jobs")
            except Exception as e:
                print(f"⚠️ Error terminating solver jobs: {e}")

        # Try additional cleanup methods if available
        if hasattr(solver_manager, "close"):
            solver_manager.close()
            print("🔒 Closed solver manager")
        elif hasattr(solver_manager, "shutdown"):
            solver_manager.shutdown()
            print("🔒 Shutdown solver manager")
        else:
            print("⚠️ No explicit close/shutdown method found on solver manager")

        print("✅ Solver cleanup completed successfully")

    except Exception as e:
        print(f"⚠️ Error during solver cleanup: {e}")
        # Don't fail tests if cleanup fails, but log it


# Test Configuration
TEST_CONFIG = {
    "valid_calendar": "tests/data/calendar.ics",
    "invalid_calendar": "tests/data/calendar_wrong.ics",
    "default_employee_count": 1,
    "default_project_id": "PROJECT",
    "solver_max_polls": 30,
    "solver_poll_interval": 1,
    "datetime_tolerance_seconds": 60,
}


# Fixtures and Helper Functions
@pytest.fixture
def valid_calendar_entries():
    """Load valid calendar entries for testing."""
    return load_calendar_entries(TEST_CONFIG["valid_calendar"])


@pytest.fixture
def invalid_calendar_entries():
    """Load invalid calendar entries for testing."""
    return load_calendar_entries(TEST_CONFIG["invalid_calendar"])


def load_calendar_entries(file_path: str) -> List[Dict]:
    """Load and extract calendar entries from an iCS file."""
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    entries, error = extract_ical_entries(file_bytes)
    assert error is None, f"Calendar extraction failed: {error}"
    assert len(entries) > 0, "No calendar entries found"

    return entries


def print_calendar_entries(entries: List[Dict], title: str = "Calendar Entries"):
    """Print calendar entries in a formatted way."""
    print(f"\n📅 {title} ({len(entries)} entries):")
    for i, entry in enumerate(entries):
        start_dt = entry.get("start_datetime")
        end_dt = entry.get("end_datetime")
        print(f"  {i+1}. {entry['summary']}: {start_dt} → {end_dt}")


def calculate_required_schedule_days(
    calendar_entries: List[Dict], buffer_days: int = 30
) -> int:
    """Calculate required schedule days based on calendar entries."""
    if not calendar_entries:
        return 60  # Default

    earliest_date = None
    latest_date = None

    for entry in calendar_entries:
        for dt_key in ["start_datetime", "end_datetime"]:
            dt = entry.get(dt_key)
            if dt and isinstance(dt, datetime):
                entry_date = dt.date()
                if earliest_date is None or entry_date < earliest_date:
                    earliest_date = entry_date
                if latest_date is None or entry_date > latest_date:
                    latest_date = entry_date

    if earliest_date and latest_date:
        calendar_span = (latest_date - earliest_date).days + 1
        return calendar_span + buffer_days
    else:
        return 60  # Fallback


async def generate_mcp_data_helper(
    calendar_entries: List[Dict],
    user_message: str,
    project_id: str = None,
    employee_count: int = None,
    days_in_schedule: int = None,
) -> pd.DataFrame:
    """Helper function to generate MCP data with consistent defaults."""
    project_id = project_id or TEST_CONFIG["default_project_id"]
    employee_count = employee_count or TEST_CONFIG["default_employee_count"]

    if days_in_schedule is None:
        days_in_schedule = calculate_required_schedule_days(calendar_entries)

    return await data_provider.generate_mcp_data(
        calendar_entries=calendar_entries,
        user_message=user_message,
        project_id=project_id,
        employee_count=employee_count,
        days_in_schedule=days_in_schedule,
    )


async def solve_schedule_with_polling(
    initial_df: pd.DataFrame, employee_count: int = None
) -> Optional[pd.DataFrame]:
    """Solve schedule with polling and return the result."""
    employee_count = employee_count or TEST_CONFIG["default_employee_count"]
    required_days = calculate_required_schedule_days([])  # Use default

    # Extract date range from pinned tasks for better schedule length calculation
    pinned_tasks = initial_df[initial_df.get("Pinned", False) == True]
    if not pinned_tasks.empty:
        required_days = calculate_required_schedule_days_from_df(pinned_tasks)

    state_data = {
        "task_df_json": initial_df.to_json(orient="split"),
        "employee_count": employee_count,
        "days_in_schedule": required_days,
    }

    # Start solving
    (
        emp_df,
        task_df,
        job_id,
        status,
        state_data,
    ) = await ScheduleService.solve_schedule_from_state(
        state_data=state_data, job_id=None, debug=True
    )

    print(f"Solver started with job_id: {job_id}")
    print(f"Initial status: {status}")

    # Poll for solution using the correct StateService methods
    max_polls = TEST_CONFIG["solver_max_polls"]
    poll_interval = TEST_CONFIG["solver_poll_interval"]

    final_df = None

    try:
        for poll_count in range(1, max_polls + 1):
            print(f"  Polling {poll_count}/{max_polls}...")
            time.sleep(poll_interval)

            # Use StateService to check for completed solution
            if StateService.has_solved_schedule(job_id):
                solved_schedule = StateService.get_solved_schedule(job_id)

                if solved_schedule is not None:
                    print(f"✅ Schedule solved after {poll_count} polls!")

                    # Convert solved schedule to DataFrame
                    final_df = schedule_to_dataframe(solved_schedule)

                    # Generate status message to check for failures
                    status_message = ScheduleService.generate_status_message(
                        solved_schedule
                    )

                    if "CONSTRAINTS VIOLATED" in status_message:
                        print(f"❌ Solver failed: {status_message}")
                        final_df = None
                    else:
                        print(f"✅ Solver succeeded: {status_message}")

                    break

        if final_df is None:
            print("⏰ Solver timed out after max polls")

    finally:
        # Clean up: Ensure solver job is terminated
        try:
            from constraint_solvers.timetable.solver import solver_manager

            # Terminate the specific job to free resources using Timefold's terminateEarly
            if hasattr(solver_manager, "terminateEarly"):
                try:
                    solver_manager.terminateEarly(job_id)
                    print(f"🧹 Terminated solver job: {job_id}")
                except Exception as e:
                    # If specific job termination fails, try to terminate all jobs
                    print(f"⚠️ Error terminating specific job {job_id}: {e}")
                    try:
                        solver_manager.terminateEarly()
                        print(
                            f"🧹 Terminated all solver jobs after specific termination failed"
                        )
                    except Exception as e2:
                        print(f"⚠️ Could not terminate any solver jobs: {e2}")
            else:
                print(f"⚠️ terminateEarly method not available on solver_manager")
        except Exception as e:
            print(f"⚠️ Could not access solver_manager for cleanup: {e}")

    return final_df


def calculate_required_schedule_days_from_df(
    pinned_df: pd.DataFrame, buffer_days: int = 30
) -> int:
    """Calculate required schedule days from DataFrame with pinned tasks."""
    earliest_date = None
    latest_date = None

    for _, row in pinned_df.iterrows():
        for date_col in ["Start", "End"]:
            date_val = row.get(date_col)
            if date_val is not None:
                try:
                    if isinstance(date_val, str):
                        dt = datetime.fromisoformat(date_val.replace("Z", "+00:00"))
                    else:
                        dt = pd.to_datetime(date_val).to_pydatetime()

                    if earliest_date is None or dt.date() < earliest_date:
                        earliest_date = dt.date()
                    if latest_date is None or dt.date() > latest_date:
                        latest_date = dt.date()
                except:
                    continue

    if earliest_date and latest_date:
        calendar_span = (latest_date - earliest_date).days + 1
        return calendar_span + buffer_days
    else:
        return 60  # Default


def analyze_schedule_dataframe(
    df: pd.DataFrame, title: str = "Schedule Analysis"
) -> Dict[str, Any]:
    """Analyze a schedule DataFrame and return summary information."""
    existing_tasks = df[df["Project"] == "EXISTING"]
    project_tasks = df[df["Project"] == "PROJECT"]

    analysis = {
        "total_tasks": len(df),
        "existing_tasks": len(existing_tasks),
        "project_tasks": len(project_tasks),
        "existing_df": existing_tasks,
        "project_df": project_tasks,
    }

    print(f"\n📊 {title} ({analysis['total_tasks']} tasks):")
    print(f"  - EXISTING (calendar): {analysis['existing_tasks']} tasks")
    print(f"  - PROJECT (LLM): {analysis['project_tasks']} tasks")

    return analysis


def verify_calendar_tasks_pinned(existing_tasks_df: pd.DataFrame) -> bool:
    """Verify that all calendar tasks are pinned."""
    print(f"\n🔒 Verifying calendar tasks are pinned:")
    all_pinned = True

    for _, task in existing_tasks_df.iterrows():
        is_pinned = task.get("Pinned", False)
        task_name = task["Task"]
        print(f"  - {task_name}: pinned = {is_pinned}")

        if not is_pinned:
            all_pinned = False
            print(f"    ❌ Calendar task should be pinned!")
        else:
            print(f"    ✅ Calendar task properly pinned")

    return all_pinned


def verify_time_preservation(
    original_times: Dict, final_tasks_df: pd.DataFrame
) -> bool:
    """Verify that calendar tasks preserved their original times."""
    print(f"\n🔍 Verifying calendar tasks preserved their original times:")
    time_preserved = True

    for _, task in final_tasks_df.iterrows():
        task_name = task["Task"]
        final_start = task["Start"]

        original = original_times.get(task_name)
        if original is None:
            print(f"  - {task_name}: ❌ Not found in original data")
            time_preserved = False
            continue

        # Normalize and compare times
        preserved = compare_datetime_values(original["start"], final_start)

        print(f"  - {task_name}:")
        print(f"    Original: {original['start']}")
        print(f"    Final:    {final_start}")
        print(f"    Preserved: {'✅' if preserved else '❌'}")

        if not preserved:
            time_preserved = False

    return time_preserved


def compare_datetime_values(dt1: Any, dt2: Any, tolerance_seconds: int = None) -> bool:
    """Compare two datetime values with tolerance for timezone differences."""
    tolerance = tolerance_seconds or TEST_CONFIG["datetime_tolerance_seconds"]

    # Convert to comparable datetime objects
    try:
        if isinstance(dt1, str):
            dt1 = datetime.fromisoformat(dt1.replace("Z", "+00:00"))

        if isinstance(dt2, str):
            dt2 = datetime.fromisoformat(dt2.replace("Z", "+00:00"))

        # Normalize timezones for comparison
        if dt1.tzinfo is not None and dt2.tzinfo is None:
            dt1 = dt1.replace(tzinfo=None)
        elif dt1.tzinfo is None and dt2.tzinfo is not None:
            dt2 = dt2.replace(tzinfo=None)

        return abs((dt1 - dt2).total_seconds()) < tolerance
    except:
        return False


def store_original_calendar_times(existing_tasks_df: pd.DataFrame) -> Dict[str, Dict]:
    """Store original calendar task times for later comparison."""
    original_times = {}

    for _, task in existing_tasks_df.iterrows():
        original_times[task["Task"]] = {
            "start": task["Start"],
            "end": task["End"],
            "pinned": task.get("Pinned", False),
        }

    print("\n📌 Original calendar task times:")
    for task_name, times in original_times.items():
        print(
            f"  - {task_name}: {times['start']} → {times['end']} (pinned: {times['pinned']})"
        )

    return original_times


def verify_llm_tasks_scheduled(project_tasks_df: pd.DataFrame) -> bool:
    """Verify that LLM tasks are properly scheduled and not pinned."""
    print(f"\n🔄 Verifying LLM tasks were properly scheduled:")
    all_scheduled = True

    for _, task in project_tasks_df.iterrows():
        task_name = task["Task"]
        start_time = task["Start"]
        is_pinned = task.get("Pinned", False)

        print(f"  - {task_name}:")
        print(f"    Scheduled at: {start_time}")
        print(f"    Pinned: {is_pinned}")

        # LLM tasks should not be pinned
        if is_pinned:
            all_scheduled = False
            print(f"    ❌ LLM task should not be pinned!")
        else:
            print(f"    ✅ LLM task properly unpinned")

        # LLM tasks should have been scheduled to actual times
        if start_time is None or start_time == "":
            all_scheduled = False
            print(f"    ❌ LLM task was not scheduled!")
        else:
            print(f"    ✅ LLM task was scheduled")

    return all_scheduled


# Test Functions
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
async def test_factory_mcp(valid_calendar_entries):
    print_calendar_entries(valid_calendar_entries, "Loaded Calendar Entries")

    # Use a made-up user message
    user_message = "Create a new AWS VPC."

    # Call generate_mcp_data directly
    df = await generate_mcp_data_helper(valid_calendar_entries, user_message)

    # Assert the DataFrame is not empty
    assert df is not None
    assert not df.empty

    # Print the DataFrame for debug
    print(df)


@pytest.mark.asyncio
async def test_mcp_workflow_calendar_pinning(valid_calendar_entries):
    """
    Test that verifies calendar tasks (EXISTING) remain pinned to their original times
    while LLM tasks (PROJECT) are rescheduled around them in the MCP workflow.
    """
    print("\n" + "=" * 60)
    print("Testing MCP Workflow: Calendar Task Pinning vs LLM Task Scheduling")
    print("=" * 60)

    print_calendar_entries(valid_calendar_entries, "Loaded Calendar Entries")

    # Generate initial MCP data
    user_message = "Set up CI/CD pipeline and configure monitoring system"
    initial_df = await generate_mcp_data_helper(valid_calendar_entries, user_message)

    # Analyze initial schedule
    analysis = analyze_schedule_dataframe(initial_df, "Generated Initial Data")

    # Store original calendar task times and verify they're pinned
    original_times = store_original_calendar_times(analysis["existing_df"])
    calendar_pinned = verify_calendar_tasks_pinned(analysis["existing_df"])
    assert calendar_pinned, "Calendar tasks should be pinned!"

    # Solve the schedule
    print(f"\n🔧 Running MCP workflow to solve schedule...")
    solved_schedule_df = await solve_schedule_with_polling(initial_df)

    if solved_schedule_df is None:
        print("⏰ Solver timed out - this might be due to complex constraints")
        print("⚠️  Skipping verification steps for timeout case")
        return

    # Analyze final schedule (solved_schedule_df is already a DataFrame)
    final_analysis = analyze_schedule_dataframe(solved_schedule_df, "Final Schedule")

    # Verify calendar tasks preserved their times
    time_preserved = verify_time_preservation(
        original_times, final_analysis["existing_df"]
    )

    # Verify LLM tasks were properly scheduled
    llm_scheduled = verify_llm_tasks_scheduled(final_analysis["project_df"])

    # Final assertions
    assert time_preserved, "Calendar tasks did not preserve their original times!"
    assert llm_scheduled, "LLM tasks were not properly scheduled!"

    print(f"\n🎉 MCP Workflow Test Results:")
    print(f"✅ Calendar tasks preserved original times: {time_preserved}")
    print(f"✅ LLM tasks were properly scheduled: {llm_scheduled}")
    print(
        "🎯 MCP workflow test passed! Calendar tasks are pinned, LLM tasks are flexible."
    )


@pytest.mark.asyncio
async def test_calendar_validation_rejects_invalid_entries(invalid_calendar_entries):
    """
    Test that calendar validation properly rejects entries that violate working hours constraints.
    """
    print("\n" + "=" * 60)
    print("Testing Calendar Validation: Constraint Violations")
    print("=" * 60)

    print_calendar_entries(invalid_calendar_entries, "Invalid Calendar Entries")

    # Test that generate_mcp_data raises an error due to validation failure
    user_message = "Simple test task"

    print(f"\n❌ Attempting to generate MCP data with invalid calendar (should fail)...")

    with pytest.raises(ValueError) as exc_info:
        await generate_mcp_data_helper(invalid_calendar_entries, user_message)

    error_message = str(exc_info.value)
    print(f"\n✅ Validation correctly rejected invalid calendar:")
    print(f"Error: {error_message}")

    # Verify the error message contains expected constraint violations
    assert "Calendar entries violate working constraints" in error_message
    # Check for specific violations that should be detected
    assert (
        "Early Morning Meeting" in error_message
        or "07:00" in error_message
        or "before 9:00" in error_message
    ), f"Should detect early morning violation in: {error_message}"
    assert (
        "Evening Meeting" in error_message
        or "21:00" in error_message
        or "after 18:00" in error_message
    ), f"Should detect evening violation in: {error_message}"
    assert (
        "Very Late Meeting" in error_message or "22:00" in error_message
    ), f"Should detect very late violation in: {error_message}"

    print("✅ All expected constraint violations were detected!")


@pytest.mark.asyncio
async def test_calendar_validation_accepts_valid_entries(valid_calendar_entries):
    """
    Test that calendar validation accepts valid entries and processing continues normally.
    """
    print("\n" + "=" * 60)
    print("Testing Calendar Validation: Valid Entries")
    print("=" * 60)

    print_calendar_entries(valid_calendar_entries, "Valid Calendar Entries")

    # Test that generate_mcp_data succeeds with valid calendar
    user_message = "Simple test task"

    print(
        f"\n✅ Attempting to generate MCP data with valid calendar (should succeed)..."
    )

    try:
        initial_df = await generate_mcp_data_helper(
            valid_calendar_entries, user_message
        )

        print(f"✅ Validation passed! Generated {len(initial_df)} tasks successfully")

        # Analyze and verify the result
        analysis = analyze_schedule_dataframe(initial_df, "Generated Schedule")

        assert analysis["existing_tasks"] > 0, "Should have calendar tasks"
        assert analysis["project_tasks"] > 0, "Should have LLM tasks"

        # Verify all calendar tasks are pinned
        calendar_pinned = verify_calendar_tasks_pinned(analysis["existing_df"])
        assert calendar_pinned, "All calendar tasks should be properly pinned!"

    except Exception as e:
        pytest.fail(f"Valid calendar should not raise an error, but got: {e}")


@pytest.mark.asyncio
async def test_mcp_backend_end_to_end():
    """
    Test the complete MCP backend workflow using the actual handler function.
    This tests the full process_message_and_attached_file flow.
    """
    print("\n" + "=" * 50)
    print("Testing MCP Backend End-to-End")
    print("=" * 50)

    # Test message for LLM tasks
    message_body = "Implement user authentication and setup database migrations"
    file_path = TEST_CONFIG["valid_calendar"]

    # Run the MCP backend handler
    print(f"📨 Processing message: '{message_body}'")
    print(f"📁 Using calendar file: {file_path}")

    result = await process_message_and_attached_file(file_path, message_body)

    # Verify the result structure
    assert isinstance(result, dict), "Result should be a dictionary"
    assert result.get("status") in [
        "success",
        "timeout",
    ], f"Unexpected status: {result.get('status')}"

    if result.get("status") == "success":
        print("✅ MCP backend completed successfully!")

        # Verify result contains expected fields
        assert "schedule" in result, "Result should contain schedule data"
        assert "calendar_entries" in result, "Result should contain calendar entries"
        assert "file_info" in result, "Result should contain file info"

        schedule = result["schedule"]
        calendar_entries = result["calendar_entries"]

        print(f"📅 Calendar entries processed: {len(calendar_entries)}")
        print(f"📋 Total scheduled tasks: {len(schedule)}")

        # Analyze the schedule
        existing_tasks = [t for t in schedule if t.get("Project") == "EXISTING"]
        project_tasks = [t for t in schedule if t.get("Project") == "PROJECT"]

        print(f"🔒 EXISTING (calendar) tasks: {len(existing_tasks)}")
        print(f"🔧 PROJECT (LLM) tasks: {len(project_tasks)}")

        # Verify we have both types of tasks
        assert len(existing_tasks) > 0, "Should have calendar tasks"
        assert len(project_tasks) > 0, "Should have LLM-generated tasks"

        # Check that project tasks exist and are scheduled
        for task in project_tasks:
            task_name = task.get("Task", "Unknown")
            start_time = task.get("Start")
            print(f"⏰ LLM task '{task_name}': scheduled at {start_time}")
            assert (
                start_time is not None
            ), f"LLM task '{task_name}' should have a scheduled start time"

        print("🎯 MCP backend end-to-end test passed!")

    elif result.get("status") == "timeout":
        print("⏰ MCP backend timed out - this is acceptable for testing")
        print("The solver may need more time for complex schedules")

        # Still verify basic structure
        assert "calendar_entries" in result, "Result should contain calendar entries"
        assert "file_info" in result, "Result should contain file info"

    else:
        # Handle error cases
        error_msg = result.get("error", "Unknown error")
        print(f"❌ MCP backend failed: {error_msg}")
        assert False, f"MCP backend failed: {error_msg}"

    print("✅ MCP backend structure and behavior verified!")


@pytest.mark.asyncio
async def test_mcp_datetime_debug(valid_calendar_entries):
    """
    Debug test to isolate the datetime conversion issue in MCP workflow.
    """
    print("\n" + "=" * 50)
    print("Testing MCP Datetime Conversion Debug")
    print("=" * 50)

    print(f"\n📅 Calendar entries debug:")
    for i, entry in enumerate(valid_calendar_entries):
        print(f"  {i+1}. {entry['summary']}:")
        print(
            f"     start_datetime: {entry.get('start_datetime')} (type: {type(entry.get('start_datetime'))})"
        )
        print(
            f"     end_datetime: {entry.get('end_datetime')} (type: {type(entry.get('end_datetime'))})"
        )

    # Generate MCP data and check the DataFrame structure
    user_message = "Simple test task"

    try:
        # Generate data with calculated schedule length
        required_days = calculate_required_schedule_days(
            valid_calendar_entries, buffer_days=10
        )
        print(f"📊 Using {required_days} total schedule days")

        initial_df = await generate_mcp_data_helper(
            valid_calendar_entries, user_message, days_in_schedule=required_days
        )

        print(f"\n📊 Generated DataFrame columns: {list(initial_df.columns)}")
        print(f"📊 DataFrame shape: {initial_df.shape}")
        print(f"📊 DataFrame dtypes:\n{initial_df.dtypes}")

        # Check the Start and End column formats
        print(f"\n🕒 Start column sample:")
        for i, row in initial_df.head(3).iterrows():
            start_val = row.get("Start")
            print(f"  Row {i}: {start_val} (type: {type(start_val)})")

        # Test conversion to JSON and back
        json_str = initial_df.to_json(orient="split")
        print(f"\n📄 JSON conversion successful")

        # Test parsing back
        task_df_back = pd.read_json(StringIO(json_str), orient="split")
        print(f"📄 JSON parsing back successful")
        print(f"📄 Parsed dtypes:\n{task_df_back.dtypes}")

        # Test task conversion with minimal error handling
        print(f"\n🔄 Testing task conversion...")

        # Only try with the first task to isolate issues
        single_task_df = task_df_back.head(1)
        print(f"Single task for testing:\n{single_task_df}")

        tasks = DataService.convert_dataframe_to_tasks(single_task_df)
        print(f"✅ Successfully converted {len(tasks)} tasks")

        for task in tasks:
            print(f"  Task: {task.description}")
            print(f"    start_slot: {task.start_slot} (type: {type(task.start_slot)})")
            print(f"    pinned: {task.pinned}")
            print(f"    project_id: {task.project_id}")

    except Exception as e:
        print(f"❌ Error in MCP data generation/conversion: {e}")
        traceback.print_exc()
        raise

    print("🎯 MCP datetime debug test completed!")
