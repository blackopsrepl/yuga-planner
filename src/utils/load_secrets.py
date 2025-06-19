import os

from utils.logging_config import setup_logging, get_logger

# Initialize logging
setup_logging()
logger = get_logger(__name__)

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
