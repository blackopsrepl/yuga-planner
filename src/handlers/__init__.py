"""
Handlers module for Yuga Planner.

This module contains handlers for web UI interactions and MCP API endpoints.
"""

from .web_backend import (
    load_data,
    show_solved,
    start_timer,
    auto_poll,
    show_mock_project_content,
)

from .mcp_backend import (
    process_message_and_attached_file,
)

from .tool_call_handler import (
    ToolCallAssembler,
    ToolCallProcessor,
    create_tool_call_handler,
)

__all__ = [
    "load_data",
    "show_solved",
    "start_timer",
    "auto_poll",
    "show_mock_project_content",
    "process_message_and_attached_file",
    "ToolCallAssembler",
    "ToolCallProcessor",
    "create_tool_call_handler",
]
