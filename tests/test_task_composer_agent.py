import pytest
import sys

from src.utils.load_secrets import load_secrets

# Import standardized test utilities
from tests.test_utils import get_test_logger, create_test_results

# Initialize standardized test logger
logger = get_test_logger(__name__)

# Load environment variables
load_secrets("tests/secrets/creds.py")
# Import task_composer_agent after environment variables are set
from src.factory.agents.task_composer_agent import TaskComposerAgent


@pytest.mark.asyncio
async def test_task_composer_agent():
    """Test the task composer agent workflow"""

    logger.start_test("Testing task composer agent workflow")

    # Create agent
    logger.debug("Initializing task_composer_agent...")
    agent = TaskComposerAgent()

    # Test input
    test_input = "Plan a weekend trip to Paris"
    logger.info(f"Test Input: {test_input}")

    # Run workflow
    logger.debug("Running agent workflow...")
    result = await agent.run_workflow(test_input)

    # Analyze results
    logger.debug("Task breakdown with estimated times:")
    for task, duration, skill in result:
        logger.debug(f"- {task}: {duration} units (Skill: {skill})")

    # Calculate total time
    total_time = sum(
        int(time) if str(time).isdigit() and str(time) != "" else 0
        for _, time, _ in result
    )
    logger.info(f"Total estimated time: {total_time} units ({total_time * 30} minutes)")

    # Verify the result is a list of 3-tuples
    assert isinstance(result, list), f"Expected a list, got {type(result)}"
    assert all(
        isinstance(item, tuple) and len(item) == 3 for item in result
    ), "Expected a list of (task, duration, skill) tuples"

    # Verify we got some tasks
    assert len(result) > 0, "Agent should return at least one task"

    logger.pass_test(
        f"Agent workflow completed - generated {len(result)} tasks, total time: {total_time} units"
    )


if __name__ == "__main__":
    """Direct execution for non-pytest testing"""
    import asyncio

    logger.section("Task Composer Agent Tests")

    # Create test results tracker
    results = create_test_results(logger)

    # Run the async test
    async def run_test():
        try:
            await test_task_composer_agent()
            return True
        except Exception as e:
            logger.fail_test("Task composer agent test", e)
            return False

    success = asyncio.run(run_test())
    results.add_result("task_composer_agent", success)

    # Generate summary and exit with appropriate code
    all_passed = results.summary()
    sys.exit(0 if all_passed else 1)
