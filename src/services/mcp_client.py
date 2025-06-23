"""
MCP Client Service for Yuga Planner

This service handles Model Context Protocol client operations for scheduling tools.
Provides a clean interface for integrating MCP scheduling functionality.
"""

import base64
from typing import Dict, Any

from utils.logging_config import setup_logging, get_logger
from handlers.mcp_backend import process_message_and_attached_file

# Initialize logging
setup_logging()
logger = get_logger(__name__)


class MCPClientService:
    """Service for MCP client operations and scheduling tool integration"""

    def __init__(self):
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "schedule_tasks_with_calendar",
                    "description": "Create an optimized schedule by analyzing calendar events and breaking down tasks. Upload a calendar .ics file and describe the task you want to schedule.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_description": {
                                "type": "string",
                                "description": "Description of the task or project to schedule (e.g., 'Create a new EC2 instance on AWS')",
                            },
                            "calendar_file_content": {
                                "type": "string",
                                "description": "Base64 encoded content of the .ics calendar file, or 'none' if no calendar provided",
                            },
                        },
                        "required": ["task_description", "calendar_file_content"],
                    },
                },
            }
        ]

    async def call_scheduling_tool(
        self, task_description: str, calendar_file_content: str
    ) -> Dict[str, Any]:
        """
        Call the scheduling backend tool.

        Args:
            task_description: Description of the task to schedule
            calendar_file_content: Base64 encoded calendar content or 'none'

        Returns:
            Dict containing the scheduling result
        """
        try:
            if calendar_file_content.lower() == "none":
                file_content = b""
            else:
                file_content = base64.b64decode(calendar_file_content)

            logger.debug(f"Calling MCP backend with task: {task_description}")
            result = await process_message_and_attached_file(
                file_content=file_content,
                message_body=task_description,
                file_name="calendar.ics",
            )

            logger.debug(
                f"MCP backend returned status: {result.get('status', 'unknown')}"
            )
            return result

        except Exception as e:
            logger.error(f"Error calling scheduling tool: {e}")
            return {"error": str(e), "status": "failed"}
