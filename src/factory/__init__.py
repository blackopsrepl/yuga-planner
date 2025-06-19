"""
Factory module for data creation - both algorithmic and AI-powered.

This module contains all data creation, generation, and formatting logic
for the Yuga Planner scheduling system, organized into:
- data: Algorithmic data generation and formatting
- agents: AI-powered task composition
"""

# Import from data submodule
from .data.formatters import schedule_to_dataframe, employees_to_dataframe
from .data.generators import (
    generate_employees,
    generate_employee_availability,
    earliest_monday_on_or_after,
)
from .data.provider import generate_agent_data, generate_mcp_data

# Import from agents submodule
from .agents.task_composer_agent import TaskComposerAgent

__all__ = [
    # Data formatters - convert domain objects to DataFrames
    "schedule_to_dataframe",
    "employees_to_dataframe",
    # Data generators - create domain objects
    "generate_employees",
    "generate_employee_availability",
    "earliest_monday_on_or_after",
    # Data providers - orchestrate data creation
    "generate_agent_data",
    "generate_mcp_data",
    # AI agents - intelligent task composition
    "TaskComposerAgent",
]
