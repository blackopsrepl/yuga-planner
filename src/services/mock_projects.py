from typing import List, Union
from domain import MOCK_PROJECTS


class MockProjectService:
    """Service for handling project-related operations"""

    @staticmethod
    def show_mock_project_content(project_names: Union[str, List[str]]) -> str:
        """
        Display the content of selected mock projects.

        Args:
            project_names: Single project name or list of project names

        Returns:
            Formatted content of the selected projects
        """
        if not project_names:
            return "No projects selected."

        # Handle both single string and list of strings
        if isinstance(project_names, str):
            project_names = [project_names]

        content_parts = []
        for project_name in project_names:
            if project_name in MOCK_PROJECTS:
                content_parts.append(
                    f"=== {project_name.upper()} ===\n\n{MOCK_PROJECTS[project_name]}"
                )
            else:
                content_parts.append(
                    f"=== {project_name.upper()} ===\n\nProject not found."
                )

        return (
            "\n\n" + "=" * 50 + "\n\n".join(content_parts)
            if content_parts
            else "No valid projects selected."
        )

    @staticmethod
    def validate_mock_projects(mock_projects: Union[str, List[str]]) -> List[str]:
        """
        Validate mock project selections and return list of invalid projects.

        Args:
            mock_projects: Single project name or list of project names

        Returns:
            List of invalid project names (empty if all valid)
        """
        if not mock_projects:
            return []

        if isinstance(mock_projects, str):
            mock_projects = [mock_projects]

        return [p for p in mock_projects if p not in MOCK_PROJECTS]

    @staticmethod
    def get_mock_project_files(mock_projects: Union[str, List[str]]) -> List[str]:
        """
        Get file contents for selected mock projects.

        Args:
            mock_projects: Single project name or list of project names

        Returns:
            List of project file contents
        """
        if isinstance(mock_projects, str):
            mock_projects = [mock_projects]

        return [
            MOCK_PROJECTS[project]
            for project in mock_projects
            if project in MOCK_PROJECTS
        ]

    @staticmethod
    def get_available_project_names() -> List[str]:
        """
        Get list of available mock project names.

        Returns:
            List of available project names
        """
        return list(MOCK_PROJECTS.keys())
