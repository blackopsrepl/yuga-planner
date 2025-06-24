"""Version utilities for the Yuga Planner application."""

import os
import re


def get_version_from_changelog():
    """Extract the latest version from CHANGELOG.md

    Returns:
        str: The latest version string (e.g., "0.6.4") or "unknown" if not found
    """
    try:
        # Get the project root directory (assuming this file is in src/utils/)
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        changelog_path = os.path.join(project_root, "CHANGELOG.md")

        with open(changelog_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Look for version pattern like ## [0.6.4]
        version_pattern = r"## \[(\d+\.\d+\.\d+)\]"
        match = re.search(version_pattern, content)

        if match:
            return match.group(1)
        else:
            return "unknown"
    except (FileNotFoundError, Exception):
        return "unknown"


# Application version - dynamically fetched from changelog
__version__ = get_version_from_changelog()
