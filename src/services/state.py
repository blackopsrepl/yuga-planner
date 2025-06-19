from typing import Optional

from state import app_state

from constraint_solvers.timetable.domain import EmployeeSchedule

from utils.logging_config import setup_logging, get_logger

# Initialize logging
setup_logging()
logger = get_logger(__name__)


class StateService:
    """Service for managing application state operations"""

    @staticmethod
    def store_solved_schedule(
        job_id: str, schedule: Optional[EmployeeSchedule]
    ) -> None:
        """
        Store a solved schedule in the application state.

        Args:
            job_id: Unique identifier for the job
            schedule: The schedule to store (can be None for placeholder)
        """
        logger.debug(f"Storing schedule for job_id: {job_id}")
        app_state.add_solved_schedule(job_id, schedule)

    @staticmethod
    def has_solved_schedule(job_id: str) -> bool:
        """
        Check if a solved schedule exists for the given job ID.

        Args:
            job_id: Job identifier to check

        Returns:
            True if a solved schedule exists for the job ID
        """
        return app_state.has_solved_schedule(job_id)

    @staticmethod
    def get_solved_schedule(job_id: str) -> Optional[EmployeeSchedule]:
        """
        Retrieve a solved schedule by job ID.

        Args:
            job_id: Job identifier to retrieve

        Returns:
            The solved schedule if it exists, None otherwise
        """
        if app_state.has_solved_schedule(job_id):
            return app_state.get_solved_schedule(job_id)
        return None

    @staticmethod
    def clear_schedule(job_id: str) -> None:
        """
        Clear a schedule from application state.

        Args:
            job_id: Job identifier to clear
        """
        logger.debug(f"Clearing schedule for job_id: {job_id}")
        # Note: app_state doesn't have a clear method, but we can implement if needed
        # For now, we'll log the request
        logger.warning(
            f"Clear schedule requested for {job_id} but not implemented in app_state"
        )

    @staticmethod
    def get_all_job_ids() -> list:
        """
        Get all job IDs currently in the state.

        Returns:
            List of job IDs
        """
        # Note: This would need to be implemented in app_state if needed
        logger.warning("get_all_job_ids called but not implemented in app_state")
        return []

    @staticmethod
    def get_state_info() -> dict:
        """
        Get general information about the current state.

        Returns:
            Dictionary with state information
        """
        # This is a placeholder for state introspection
        return {
            "service": "StateService",
            "status": "active",
            "note": "State information retrieval not fully implemented",
        }
