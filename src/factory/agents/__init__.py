"""
Agents module for AI-powered data creation.

This module contains all AI-based task composition and data generation logic
for the Yuga Planner scheduling system.
"""

from .task_composer_agent import TaskComposerAgent
from .task_processing import (
    remove_markdown_code_blocks,
    remove_markdown_list_elements,
    unwrap_tasks_from_generated,
    log_task_duration_breakdown,
    log_total_time,
)

__all__ = [
    # Main agent class
    "TaskComposerAgent",
    # Task processing utilities
    "remove_markdown_code_blocks",
    "remove_markdown_list_elements",
    "unwrap_tasks_from_generated",
    "log_task_duration_breakdown",
    "log_total_time",
]
