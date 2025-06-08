import os, logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

### SECRETS ###
def load_secrets(secrets_file: str):
    """
    Load secrets from Python file into environment variables.

    Args:
        secrets_file (str): Path to the Python file containing secrets

    Returns:
        bool: True if secrets were loaded successfully
    """
    try:
        # Import secrets from the specified file
        import importlib.util

        spec = importlib.util.spec_from_file_location("secrets", secrets_file)
        secrets = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(secrets)

        # Set environment variables
        os.environ["NEBIUS_API_KEY"] = secrets.NEBIUS_API_KEY
        os.environ["NEBIUS_MODEL"] = secrets.NEBIUS_MODEL
        return True

    except Exception as e:
        logger.error(f"Failed to load secrets from {secrets_file}: {str(e)}")
        return False


### MARKDOWN UTILS ###
def remove_markdown_code_blocks(text: str) -> str:
    """
    Remove markdown code block syntax from text.

    Args:
        text (str): Text that may contain markdown code block syntax

    Returns:
        str: Text with markdown code block syntax removed
    """
    content = text

    if content.startswith("```markdown"):
        content = content[11:]  # Remove ```markdown

    if content.endswith("```"):
        content = content[:-3]  # Remove ```

    return content.strip()


def unwrap_tasks_from_generated(result: list) -> list:
    """
    Extract task text from the generated markdown list structure.

    Args:
        result (list): List containing markdown list structure

    Returns:
        list: List of task text strings
    """
    tasks = []

    # Input validation: check if result is a list
    if not isinstance(result, list):
        logger.error("Error: 'Unordered list' is not a list!")
        return tasks

    # We expect result to be a list of lists, with only one entry
    if not isinstance(result[0], list):
        logger.error("Error: The first element of the result is not a list!")
        return tasks

    # Unwrap the inner list of dictionaries
    for task in result[0]:
        if isinstance(task, dict) and "text" in task:
            tasks.append(task["text"])
        else:
            logger.warning(f"Unexpected task format: {task}")

    return tasks


### LOGGING ###
def log_task_duration_breakdown(merged_tasks: list[tuple[str, str]]) -> None:
    """
    Log the duration breakdown for each task.

    Args:
        merged_tasks (list[tuple[str, str]]): List of (task, duration) tuples
    """
    logger.info("Task duration breakdown:")

    for task, duration in merged_tasks:
        logger.info(f"- {task}: {duration} units")


def log_total_time(merged_tasks: list[tuple[str, str]]) -> None:
    """
    Log the total estimated time for all tasks.

    Args:
        merged_tasks (list[tuple[str, str]]): List of (task, duration) tuples
    """
    total_time = sum(int(time) for _, time in merged_tasks)

    logger.info("Estimated time:")
    logger.info(f"{total_time} units (30 minutes each)")
