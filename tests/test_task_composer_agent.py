import pytest, logging

from utils.agent_utils import load_secrets

# Load environment variables
print("\n=== Test Environment ===")
load_secrets("tests/secrets/nebius_secrets.py")

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Import TaskComposerAgent after environment variables are set
from src.agents.TaskComposerAgent import TaskComposerAgent


@pytest.mark.asyncio
async def test_task_composer_agent():
    print("\n=== Starting Test ===")

    # Create agent
    print("\nInitializing TaskComposerAgent...")
    agent = TaskComposerAgent()

    # Test input
    test_input = "Plan a weekend trip to Paris"
    print(f"\n=== Test Input ===")
    print(f"Task: {test_input}")

    # Run workflow
    print("\n=== Running Workflow ===")
    result = await agent.run_workflow(test_input)

    # Print the result
    print(f"\n=== Final Result ===")
    print("Task breakdown with estimated times:")
    for task, duration in result:
        print(f"- {task}: {duration} units")

    # Calculate total time
    total_time = sum(int(time) for _, time in result)
    print(f"\nTotal estimated time: {total_time} units ({total_time * 30} minutes)")

    # Verify the result is a list of tuples
    assert isinstance(result, list), f"Expected a list, got {type(result)}"
    assert all(
        isinstance(item, tuple) and len(item) == 2 for item in result
    ), "Expected a list of (task, duration) tuples"
    print("\n=== Test Summary ===")
    print("✓ Test passed!")
    print(f"✓ Task: {test_input}")
    print(f"✓ Total estimated time: {total_time} units ({total_time * 30} minutes)")
