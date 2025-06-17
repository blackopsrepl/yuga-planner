import pytest, logging


from src.utils.load_secrets import load_secrets

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables
load_secrets("tests/secrets/creds.py")
# Import task_composer_agent after environment variables are set
from src.agents.task_composer_agent import TaskComposerAgent


@pytest.mark.asyncio
async def test_task_composer_agent():
    logger.info("\n=== Test Environment ===")

    logger.info("\n=== Starting Test ===")

    # Create agent
    logger.info("\nInitializing task_composer_agent...")
    agent = TaskComposerAgent()

    # Test input
    test_input = "Plan a weekend trip to Paris"
    logger.info(f"\n=== Test Input ===")
    logger.info(f"Task: {test_input}")

    # Run workflow
    logger.info("\n=== Running Workflow ===")
    result = await agent.run_workflow(test_input)

    # Print the result
    logger.info(f"\n=== Final Result ===")
    logger.info("Task breakdown with estimated times:")
    for task, duration, skill in result:
        logger.info(f"- {task}: {duration} units (Skill: {skill})")

    # Calculate total time
    total_time = sum(
        int(time) if str(time).isdigit() and str(time) != "" else 0
        for _, time, _ in result
    )
    logger.info(
        f"\nTotal estimated time: {total_time} units ({total_time * 30} minutes)"
    )

    # Verify the result is a list of 3-tuples
    assert isinstance(result, list), f"Expected a list, got {type(result)}"
    assert all(
        isinstance(item, tuple) and len(item) == 3 for item in result
    ), "Expected a list of (task, duration, skill) tuples"
    logger.info("\n=== Test Summary ===")
    logger.info("✓ Test passed!")
    logger.info(f"✓ Task: {test_input}")
    logger.info(
        f"✓ Total estimated time: {total_time} units ({total_time * 30} minutes)"
    )
