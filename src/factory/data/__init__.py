"""
Data module for data generation, transformation, and formatting.

This module contains all algorithmic data creation, generation, and formatting logic
for the Yuga Planner scheduling system.
"""

from .formatters import schedule_to_dataframe, employees_to_dataframe
from .generators import (
    generate_employees,
    generate_employee_availability,
    earliest_monday_on_or_after,
)
from .provider import generate_agent_data, generate_mcp_data

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
]
