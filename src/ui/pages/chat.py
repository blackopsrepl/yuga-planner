import os, json, re, traceback, asyncio
import gradio as gr

from typing import Generator
from datetime import datetime, date

import requests

from handlers.tool_call_handler import create_tool_call_handler
from services.mcp_client import MCPClientService
from services.constraint_analyzer import ConstraintAnalyzerService
from constraint_solvers.timetable.domain import EmployeeSchedule

from utils.load_secrets import load_secrets

if not os.getenv("NEBIUS_API_KEY") or not os.getenv("NEBIUS_MODEL"):
    load_secrets("tests/secrets/creds.py")

nebius_api_key = os.getenv("NEBIUS_API_KEY")
nebius_model = os.getenv("NEBIUS_MODEL")

from utils.logging_config import (
    setup_logging,
    get_logger,
    start_session_logging,
    get_session_logs,
)

# Initialize logging
setup_logging()
logger = get_logger(__name__)

# Global MCP client for the chat page
_mcp_client = None
_tool_assembler = None
_tool_processor = None

# Get or create event loop for MCP operations
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects and other non-serializable types"""

    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif hasattr(obj, "__dict__"):
            return str(obj)
        elif hasattr(obj, "to_dict"):
            return obj.to_dict()
        else:
            return str(obj)


def safe_json_dumps(obj, **kwargs):
    """Safely serialize objects to JSON, handling datetime and other non-serializable types"""
    try:
        return json.dumps(obj, cls=DateTimeEncoder, **kwargs)
    except Exception as e:
        logger.warning(
            f"JSON serialization failed: {e}, falling back to string representation"
        )
        return json.dumps(
            {"error": f"Serialization failed: {str(e)}", "raw_data": str(obj)[:1000]},
            **kwargs,
        )


def format_heatmap_data(heatmap_data: dict) -> str:
    """Format heatmap data for display in the chat interface"""
    if not heatmap_data:
        return "🟢 **No constraint violations detected** - All entities are performing well!"

    formatted_output = "\n\n## 🔥 **Constraint Violation Heatmap**\n\n"
    formatted_output += "This heatmap shows which tasks and employees have the most constraint violations:\n\n"

    # Separate tasks and employees
    task_violations = {}
    employee_violations = {}

    for entity, data in heatmap_data.items():
        entity_name = str(entity)
        if hasattr(entity, "description"):  # This is a task
            task_violations[entity] = data
        elif hasattr(entity, "name"):  # This is an employee
            employee_violations[entity] = data
        else:
            # Fallback - try to determine by content
            if "Task" in entity_name or "task" in entity_name.lower():
                task_violations[entity] = data
            else:
                employee_violations[entity] = data

    # Sort by severity (hard score first, then soft score)
    def get_severity(item):
        _, data = item
        return (abs(data["hard_score"]), abs(data["soft_score"]))

    # Display task violations
    if task_violations:
        sorted_tasks = sorted(task_violations.items(), key=get_severity, reverse=True)
        formatted_output += "### 📋 **Task Constraint Violations**\n\n"

        for i, (task, data) in enumerate(
            sorted_tasks[:10]
        ):  # Show top 10 most problematic
            # Get severity indicators
            severity = (
                "🔴"
                if data["hard_score"] < -5
                else "🟡"
                if data["hard_score"] < 0
                else "🟢"
            )

            task_name = getattr(task, "description", str(task))[:50]
            if len(getattr(task, "description", str(task))) > 50:
                task_name += "..."

            formatted_output += f"{severity} **{task_name}**\n"
            formatted_output += f"   - Hard Score: {data['hard_score']} | Soft Score: {data['soft_score']}\n"

            # Show constraint matches
            if data["constraint_matches"]:
                formatted_output += f"   - Violations: "
                constraint_names = [
                    match["constraint_name"] for match in data["constraint_matches"][:3]
                ]
                formatted_output += ", ".join(constraint_names)
                if len(data["constraint_matches"]) > 3:
                    formatted_output += (
                        f" (+{len(data['constraint_matches']) - 3} more)"
                    )
                formatted_output += "\n"
            formatted_output += "\n"

    # Display employee violations
    if employee_violations:
        sorted_employees = sorted(
            employee_violations.items(), key=get_severity, reverse=True
        )
        formatted_output += "### 👥 **Employee Constraint Violations**\n\n"

        for employee, data in sorted_employees:
            # Get severity indicators
            severity = (
                "🔴"
                if data["hard_score"] < -5
                else "🟡"
                if data["hard_score"] < 0
                else "🟢"
            )

            employee_name = getattr(employee, "name", str(employee))
            formatted_output += f"{severity} **{employee_name}**\n"
            formatted_output += f"   - Hard Score: {data['hard_score']} | Soft Score: {data['soft_score']}\n"

            # Show constraint matches
            if data["constraint_matches"]:
                formatted_output += f"   - Violations: "
                constraint_names = [
                    match["constraint_name"] for match in data["constraint_matches"][:3]
                ]
                formatted_output += ", ".join(constraint_names)
                if len(data["constraint_matches"]) > 3:
                    formatted_output += (
                        f" (+{len(data['constraint_matches']) - 3} more)"
                    )
                formatted_output += "\n"
            formatted_output += "\n"

    # Add summary
    total_entities = len(heatmap_data)
    high_severity = sum(1 for data in heatmap_data.values() if data["hard_score"] < -5)
    medium_severity = sum(
        1 for data in heatmap_data.values() if -5 <= data["hard_score"] < 0
    )

    formatted_output += f"### 📊 **Violation Summary**\n\n"
    formatted_output += f"- 🔴 **High Severity:** {high_severity} entities\n"
    formatted_output += f"- 🟡 **Medium Severity:** {medium_severity} entities\n"
    formatted_output += f"- 📈 **Total Affected:** {total_entities} entities\n"

    return formatted_output


def create_constraint_analysis(schedule_dict: dict) -> str:
    """Create a comprehensive constraint analysis including heatmap for the schedule"""
    try:
        # Try to reconstruct the EmployeeSchedule from the result dictionary
        from constraint_solvers.timetable.domain import (
            EmployeeSchedule,
            Employee,
            Task,
            ScheduleInfo,
        )

        # Check if we have the necessary data
        if not isinstance(schedule_dict, dict):
            return ""

        # Look for schedule data in different possible locations
        schedule_data = None
        if "schedule" in schedule_dict:
            schedule_data = schedule_dict["schedule"]
        elif isinstance(schedule_dict, list):
            schedule_data = schedule_dict
        else:
            # Try to find schedule-like data
            for key, value in schedule_dict.items():
                if isinstance(value, list) and len(value) > 0:
                    if any(
                        "Task" in str(item) or "Employee" in str(item)
                        for item in value[:3]
                    ):
                        schedule_data = value
                        break

        if not schedule_data:
            logger.info("No schedule data found for constraint analysis")
            return ""

        # For now, since we don't have the full EmployeeSchedule object,
        # we'll create a simplified analysis based on the schedule data
        analysis_output = "\n\n## 🧠 **Constraint Analysis**\n\n"

        # Analyze the schedule data for potential issues
        total_tasks = len(schedule_data)
        pinned_tasks = sum(1 for item in schedule_data if item.get("Pinned", False))
        unavailable_conflicts = sum(
            1 for item in schedule_data if item.get("Unavailable", False)
        )
        undesired_assignments = sum(
            1 for item in schedule_data if item.get("Undesired", False)
        )
        desired_assignments = sum(
            1 for item in schedule_data if item.get("Desired", False)
        )

        # Calculate constraint health score
        if total_tasks > 0:
            health_score = max(
                0, 100 - (unavailable_conflicts * 30) - (undesired_assignments * 10)
            )

            if health_score >= 90:
                status_icon = "🟢"
                status_text = "Excellent"
            elif health_score >= 70:
                status_icon = "🟡"
                status_text = "Good"
            elif health_score >= 50:
                status_icon = "🟠"
                status_text = "Fair"
            else:
                status_icon = "🔴"
                status_text = "Poor"

            analysis_output += f"### {status_icon} **Schedule Health: {status_text} ({health_score}/100)**\n\n"

            # Only show constraint-specific details if there are violations or issues
            has_violations = unavailable_conflicts > 0 or undesired_assignments > 0
            has_preferences = desired_assignments > 0

            if has_violations or has_preferences:
                analysis_output += f"**🎯 Constraint Details:**\n"
                if unavailable_conflicts > 0:
                    analysis_output += (
                        f"- ❌ Unavailable Conflicts: {unavailable_conflicts}\n"
                    )
                if undesired_assignments > 0:
                    analysis_output += (
                        f"- 😐 Undesired Assignments: {undesired_assignments}\n"
                    )
                if desired_assignments > 0:
                    analysis_output += (
                        f"- ✅ Desired Assignments: {desired_assignments}\n"
                    )
                analysis_output += "\n"

            # Only show issues and suggestions if there are actual problems
            if has_violations:
                if unavailable_conflicts > 0:
                    analysis_output += f"⚠️ **Hard Constraint Violations:** {unavailable_conflicts} tasks scheduled when employees are unavailable\n\n"

                if undesired_assignments > 0:
                    analysis_output += f"⚠️ **Soft Constraint Violations:** {undesired_assignments} tasks scheduled on undesired dates\n\n"

                # Suggestions only when there are actual problems
                suggestions = []
                if unavailable_conflicts > 0:
                    suggestions.append(
                        "🔧 **Reschedule unavailable assignments** - Move tasks to available time slots"
                    )
                if undesired_assignments > 5:
                    suggestions.append(
                        "🔧 **Optimize employee preferences** - Consider redistributing tasks on undesired dates"
                    )
                elif undesired_assignments > 0:
                    suggestions.append(
                        "🔧 **Minor optimization** - Consider adjusting a few undesired assignments"
                    )

                if suggestions:
                    analysis_output += f"### 💡 **Improvement Suggestions**\n\n"
                    for suggestion in suggestions:
                        analysis_output += f"- {suggestion}\n"
                    analysis_output += "\n"
            else:
                # Perfect schedule - just acknowledge it briefly
                analysis_output += f"✨ **Perfect constraint satisfaction** - No conflicts or violations detected!\n\n"

            # Employee workload analysis - only show if multiple employees or workload issues exist
            employee_workload = {}
            for item in schedule_data:
                employee = item.get("Employee", "Unassigned")
                if employee not in employee_workload:
                    employee_workload[employee] = {
                        "tasks": 0,
                        "hours": 0,
                        "unavailable": 0,
                        "undesired": 0,
                        "desired": 0,
                    }
                employee_workload[employee]["tasks"] += 1
                employee_workload[employee]["hours"] += item.get("Duration (hours)", 0)
                if item.get("Unavailable", False):
                    employee_workload[employee]["unavailable"] += 1
                if item.get("Undesired", False):
                    employee_workload[employee]["undesired"] += 1
                if item.get("Desired", False):
                    employee_workload[employee]["desired"] += 1

            # Only show workload analysis if there are multiple employees OR workload issues
            active_employees = [
                emp for emp in employee_workload.keys() if emp != "Unassigned"
            ]
            has_workload_issues = any(
                workload["unavailable"] > 0 or workload["undesired"] > 0
                for workload in employee_workload.values()
            )

            if len(active_employees) > 1 or has_workload_issues:
                analysis_output += f"### 👥 **Employee Workload Analysis**\n\n"

                for employee, workload in sorted(
                    employee_workload.items(), key=lambda x: x[1]["hours"], reverse=True
                ):
                    if employee != "Unassigned":
                        violation_score = (
                            workload["unavailable"] * 2 + workload["undesired"]
                        )
                        if violation_score >= 3:
                            stress_icon = "🔴"
                        elif violation_score >= 1:
                            stress_icon = "🟡"
                        else:
                            stress_icon = "🟢"

                        analysis_output += f"{stress_icon} **{employee}**: {workload['tasks']} tasks, {workload['hours']}h"
                        if workload["unavailable"] > 0 or workload["undesired"] > 0:
                            analysis_output += f" (⚠️ {workload['unavailable']} unavailable, {workload['undesired']} undesired)"
                        analysis_output += "\n"
                analysis_output += "\n"

        else:
            analysis_output += "No tasks found for analysis.\n"

        return analysis_output

    except Exception as e:
        logger.error(f"Error creating constraint analysis: {e}")
        return f"\n\n⚠️ **Constraint analysis unavailable:** {str(e)}\n"


def draw_chat_page(debug: bool = False):
    logger.info(f"NEBIUS_MODEL: {nebius_model}")
    logger.info(f"NEBIUS_API_KEY: {'Set' if nebius_api_key else 'Not Set'}")

    if not nebius_model or not nebius_api_key:
        logger.error(
            "NEBIUS_MODEL or NEBIUS_API_KEY not found in environment variables"
        )

    with gr.Tab("💬 Chat Agent Demo"):
        gr.Markdown(
            """
            # 💬 Chat Agent Demo

            This is a chat agent demo for Yuga Planner!

            Insert a task description to have the agent schedule it standalone or around your existing calendar.

            If you provide a .ics file, the schedule will start from **the first occupied time slot in your calendar file**.

            If you don't, the schedule will start from **next monday**.
            """
        )

        if not nebius_model or not nebius_api_key:
            gr.Markdown(
                """
                ⚠️ **Chat unavailable**: NEBIUS_MODEL or NEBIUS_API_KEY environment variables are not set.

                Please configure your Nebius credentials to use the chat feature.
                """
            )
            return

        # Initialize MCP client and tool handlers as globals for this page
        global _mcp_client, _tool_assembler, _tool_processor
        _mcp_client = MCPClientService()
        _tool_assembler, _tool_processor = create_tool_call_handler(_mcp_client)

        # Create chat interface components
        (
            chatbot,
            msg,
            clear,
            stop,
            calendar_file,
            constraint_analysis,
        ) = create_chat_interface()

        # Create parameter controls
        (
            system_message,
            max_tokens_slider,
            temperature_slider,
            top_p_slider,
        ) = create_chatbot_parameters()

        # Handle message submission
        submit_event = msg.submit(
            user_message,
            [msg, chatbot, calendar_file],
            [msg, chatbot, msg, stop],
            queue=False,
        ).then(
            bot_response,
            [
                chatbot,
                system_message,
                max_tokens_slider,
                temperature_slider,
                top_p_slider,
            ],
            [chatbot, msg, stop, constraint_analysis],
            show_progress=True,
        )

        # Handle clear button
        def clear_chat():
            return (
                [],  # Clear chatbot
                gr.update(interactive=True),  # Enable msg input
                gr.update(visible=False),  # Hide stop button
                "## 🧠 **Constraint Analysis**\n\n*Schedule a task to see constraint analysis...*",  # Reset constraint analysis
            )

        clear.click(
            clear_chat, None, [chatbot, msg, stop, constraint_analysis], queue=False
        )

        # Handle stop button
        def stop_processing():
            return gr.update(interactive=True), gr.update(visible=False)

        stop.click(
            stop_processing, None, [msg, stop], queue=False, cancels=[submit_event]
        )


def create_chat_interface() -> tuple[
    gr.Chatbot, gr.Textbox, gr.Button, gr.Button, gr.File, gr.Markdown
]:
    """Create and return the chat interface components"""

    # Create main layout with chat on left and analysis on right
    with gr.Row():
        # Left column - Chat interface
        with gr.Column(scale=2):
            chatbot = gr.Chatbot(type="messages", height=500)

        # Right column - Constraint Analysis only
        with gr.Column(scale=1):
            constraint_analysis = gr.Markdown(
                value="## 🧠 **Constraint Analysis**\n\n*Schedule a task to see constraint analysis...*",
                label="Schedule Analysis",
                container=True,
                elem_id="constraint-analysis-panel",
            )

    # Calendar upload - spans full width, above message input
    calendar_file = gr.UploadButton(
        "📅 Upload Calendar (.ics) - Optional",
        file_types=[".ics"],
        file_count="single",
        variant="secondary",
        size="md",
        elem_id="calendar-upload",
    )

    # Message input row - spans full width
    msg = gr.Textbox(
        label="Insert a task description",
        placeholder="Ex.: Create a new EC2 instance on AWS",
        interactive=True,
        container=True,
        lines=1,
        max_lines=3,
    )

    # Control buttons row - spans full width
    with gr.Row():
        clear = gr.Button("Clear", variant="secondary")
        stop = gr.Button("Stop", variant="stop", visible=False)

    return chatbot, msg, clear, stop, calendar_file, constraint_analysis


def create_chatbot_parameters() -> tuple[gr.Textbox, gr.Slider, gr.Slider, gr.Slider]:
    """Create and return the chatbot parameter controls"""
    with gr.Accordion("Chatbot Parameters", open=False):
        system_message = gr.Textbox(
            value="You are a friendly and helpful AI assistant that specializes in task scheduling and productivity. You can help users plan and organize their work around existing calendar commitments. When users ask about scheduling tasks or mention calendar-related activities, you should use the schedule_tasks_with_calendar tool to create optimized schedules. If you see [Calendar file uploaded:] in a message, the user has provided calendar data that should be used for scheduling. Always use the scheduling tool when users mention tasks, projects, scheduling, planning, or similar requests.",
            label="System message",
        )
        max_tokens_slider = gr.Slider(
            minimum=1, maximum=2048, value=512, step=1, label="Max new tokens"
        )
        temperature_slider = gr.Slider(
            minimum=0.1, maximum=4.0, value=0.7, step=0.1, label="Temperature"
        )
        top_p_slider = gr.Slider(
            minimum=0.1,
            maximum=1.0,
            value=0.95,
            step=0.05,
            label="Top-p (nucleus sampling)",
        )
    return system_message, max_tokens_slider, temperature_slider, top_p_slider


def user_message(message, history, calendar_file_obj):
    # Handle calendar file upload
    enhanced_message = message

    # Use provided calendar file or default to empty.ics
    if calendar_file_obj is not None:
        # Read and encode the uploaded calendar file
        try:
            import base64

            with open(calendar_file_obj, "rb") as f:
                file_content = f.read()

            encoded_content = base64.b64encode(file_content).decode("utf-8")
            enhanced_message += (
                f"\n\n[Calendar file uploaded: {calendar_file_obj.name}]"
            )
            enhanced_message += f"\n[CALENDAR_DATA:{encoded_content}]"
        except Exception as e:
            logger.error(f"Error reading calendar file: {e}")
            enhanced_message += f"\n\n[Calendar file upload failed: {str(e)}]"
    else:
        # Use empty.ics as default when no calendar is provided
        try:
            import base64

            empty_calendar_path = "tests/data/empty.ics"
            with open(empty_calendar_path, "rb") as f:
                file_content = f.read()

            encoded_content = base64.b64encode(file_content).decode("utf-8")
            enhanced_message += f"\n\n[Default empty calendar used]"
            enhanced_message += f"\n[CALENDAR_DATA:{encoded_content}]"
        except Exception as e:
            logger.error(f"Error reading default empty calendar: {e}")
            enhanced_message += f"\n\n[Default calendar load failed: {str(e)}]"

    return (
        "",  # Clear input
        history + [{"role": "user", "content": enhanced_message}],
        gr.update(interactive=False),  # Disable input
        gr.update(visible=True),  # Show stop button
    )


def bot_response(history, system_message, max_tokens, temperature, top_p):
    if not history:
        return (
            history,
            gr.update(interactive=True),
            gr.update(visible=False),
            "## 🧠 **Constraint Analysis**\n\n*Schedule a task to see constraint analysis...*",
        )

    # Convert messages format to tuples for the respond function
    history_tuples = []
    for msg in history[:-1]:  # All but the last message
        if msg["role"] == "user":
            history_tuples.append([msg["content"], ""])
        elif msg["role"] == "assistant":
            if history_tuples:
                history_tuples[-1][1] = msg["content"]
            else:
                history_tuples.append(["", msg["content"]])

    # Get the last user message
    user_msg = history[-1]["content"]

    logger.info(f"Bot response called with user message: {user_msg[:100]}...")

    # Store the latest constraint analysis to return
    latest_constraint_analysis = "## 🧠 **Constraint Analysis**\n\n*Processing...*"

    try:
        # Get the response generator
        response_gen = respond(
            user_msg,
            history_tuples,
            system_message,
            max_tokens,
            temperature,
            top_p,
        )

        # Stream responses to show progress - this is a generator function now
        for response_chunk, constraint_analysis_chunk in response_gen:
            updated_history = history.copy()
            updated_history[-1] = {"role": "assistant", "content": response_chunk}
            latest_constraint_analysis = constraint_analysis_chunk
            yield (
                updated_history,
                gr.update(),  # Keep input disabled during processing
                gr.update(),  # Keep stop button visible
                constraint_analysis_chunk,  # Update constraint analysis panel
            )

        # Final yield to re-enable input and hide stop button
        final_history = history.copy()
        final_history[-1] = {"role": "assistant", "content": response_chunk}
        yield (
            final_history,
            gr.update(interactive=True),  # Re-enable input
            gr.update(visible=False),  # Hide stop button
            latest_constraint_analysis,  # Final constraint analysis
        )

    except Exception as e:
        logger.error(f"Error in bot_response: {e}")
        import traceback

        logger.error(f"Full traceback: {traceback.format_exc()}")
        error_history = history.copy()
        error_history[-1] = {"role": "assistant", "content": f"Error: {str(e)}"}
        yield (
            error_history,
            gr.update(interactive=True),  # Re-enable input on error
            gr.update(visible=False),  # Hide stop button on error
            "## 🧠 **Constraint Analysis**\n\n❌ **Error occurred during analysis**",  # Error state for constraint analysis
        )


def respond(
    message,
    history: list[tuple[str, str]],
    system_message,
    max_tokens,
    temperature,
    top_p,
) -> Generator[tuple[str, str], None, None]:
    try:
        # Start capturing logs for this session
        start_session_logging()

        # Reset tool assembler for new conversation
        _tool_assembler.reset()

        messages = [{"role": "system", "content": system_message}]

        for val in history:
            if val[0]:
                messages.append({"role": "user", "content": val[0]})

            if val[1]:
                messages.append({"role": "assistant", "content": val[1]})

        messages.append({"role": "user", "content": message})

        # Check if this looks like a scheduling request
        scheduling_keywords = [
            "schedule",
            "task",
            "calendar",
            "plan",
            "organize",
            "meeting",
            "appointment",
            "project",
            "deadline",
            "create",
            "setup",
            "implement",
            "develop",
        ]

        is_scheduling_request = any(
            keyword in message.lower() for keyword in scheduling_keywords
        )

        logger.info(f"Message: {message}")
        logger.info(f"Is scheduling request: {is_scheduling_request}")

        # Prepare payload for Nebius API
        payload = {
            "model": nebius_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stream": True,
        }

        # Add tools if this might be a scheduling request
        if is_scheduling_request:
            logger.info("Adding tools to payload")
            payload["tools"] = _mcp_client.tools
            payload["tool_choice"] = "auto"
            logger.debug(f"Tools payload: {_mcp_client.tools}")

        else:
            logger.info("No scheduling detected, not adding tools")

        headers = {
            "Authorization": f"Bearer {nebius_api_key}",
            "Content-Type": "application/json",
        }

        logger.info(
            f"Sending request to Nebius API with tools: {is_scheduling_request}"
        )
        logger.debug(f"Full payload: {json.dumps(payload, indent=2)}")

        response = requests.post(
            "https://api.studio.nebius.ai/v1/chat/completions",
            headers=headers,
            json=payload,
            stream=True,
        )

        if response.status_code != 200:
            logger.error(f"API error: {response.status_code} - {response.text}")
            yield (
                f"Error: API returned {response.status_code}: {response.text}",
                "## 🧠 **Constraint Analysis**\n\n❌ **API Error**",
            )
            return

        response_text = ""
        constraint_analysis_text = "## 🧠 **Constraint Analysis**\n\n*Processing...*"

        # Initial yield to show streaming is working
        if is_scheduling_request:
            yield (
                "🤖 **Processing your scheduling request...**",
                constraint_analysis_text,
            )

        for line in response.iter_lines():
            if line:
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    data = line[6:]  # Remove 'data: ' prefix
                    if data.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        logger.debug(f"Received chunk: {chunk}")
                        if "choices" in chunk and len(chunk["choices"]) > 0:
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content", "")

                            if content:
                                response_text += content

                                # For scheduling requests, include essential logs inline
                                if is_scheduling_request:
                                    session_logs = get_session_logs()

                                    if session_logs:
                                        # Show only new logs since last yield
                                        latest_logs = (
                                            session_logs[-3:]
                                            if len(session_logs) > 3
                                            else session_logs
                                        )
                                        logs_text = "\n".join(
                                            f"  {log}" for log in latest_logs
                                        )

                                        yield (
                                            response_text + f"\n\n{logs_text}",
                                            constraint_analysis_text,
                                        )

                                    else:
                                        yield (response_text, constraint_analysis_text)

                                else:
                                    yield (response_text, constraint_analysis_text)

                            # Process tool calls using our new handler
                            _tool_assembler.process_delta(delta)

                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decode error: {e} for line: {line}")
                        continue

        # Get completed tool calls and process them
        completed_tool_calls = _tool_assembler.get_completed_tool_calls()

        # Log debug info
        debug_info = _tool_assembler.debug_info()
        logger.info(f"Tool call assembly completed: {debug_info}")

        if completed_tool_calls:
            logger.info(f"Processing {len(completed_tool_calls)} completed tool calls")
            yield (
                response_text + "\n\n🔧 **Processing scheduling request...**",
                constraint_analysis_text,
            )

            # Process tool calls using our new processor
            tool_response = _tool_processor.process_tool_calls(
                completed_tool_calls, message
            )
            response_text += tool_response

            # Extract constraint analysis from tool response if present
            if "🧠 **Constraint Analysis**" in tool_response:
                # Split the response to separate chat content from constraint analysis
                parts = tool_response.split("## 🧠 **Constraint Analysis**")
                if len(parts) > 1:
                    chat_content = parts[0]
                    analysis_content = "## 🧠 **Constraint Analysis**" + parts[1]
                    # Clean up any duplicate analysis sections
                    if "<details>" in analysis_content:
                        analysis_content = analysis_content.split("<details>")[0]
                    constraint_analysis_text = analysis_content.strip()
                    response_text = response_text.replace(tool_response, chat_content)

            yield (response_text, constraint_analysis_text)

        else:
            logger.info("No completed tool calls found")
            if is_scheduling_request:
                logger.warning(
                    "Scheduling request detected but no completed tool calls"
                )

                # Log detailed debug info for troubleshooting
                logger.error(f"Tool assembly debug info: {debug_info}")

                yield (
                    response_text
                    + "\n\n⚠️ **Scheduling request detected but tool not triggered or incomplete. Let me try calling the scheduler directly...**",
                    constraint_analysis_text,
                )

                # Directly call the scheduling tool as fallback
                try:
                    # Extract task description from message
                    task_description = message
                    calendar_content = ""  # Always start with empty calendar

                    # Extract calendar data if available
                    calendar_match = re.search(r"\[CALENDAR_DATA:([^\]]+)\]", message)

                    if calendar_match:
                        calendar_content = calendar_match.group(1)
                        logger.info("Calendar data found and extracted")

                    else:
                        # If no calendar data found, proceed with empty calendar
                        logger.info(
                            "No calendar data found, proceeding with empty calendar - tool will still be called"
                        )

                    # Show essential task processing logs inline
                    session_logs = get_session_logs()
                    processing_status = ""

                    if session_logs:
                        latest_logs = (
                            session_logs[-2:] if len(session_logs) > 2 else session_logs
                        )
                        processing_status = "\n" + "\n".join(
                            f"  {log}" for log in latest_logs
                        )

                    yield (
                        response_text
                        + f"\n\n🔧 **Direct scheduling call for: {task_description}**\n⏳ *Processing...*{processing_status}",
                        constraint_analysis_text,
                    )

                    logger.info("About to call MCP scheduling tool directly")

                    # Add timeout to prevent hanging
                    def call_with_timeout():
                        try:
                            return loop.run_until_complete(
                                asyncio.wait_for(
                                    _mcp_client.call_scheduling_tool(
                                        task_description, calendar_content
                                    ),
                                    timeout=60.0,  # 60 second timeout
                                )
                            )
                        except asyncio.TimeoutError:
                            return {
                                "error": "Timeout after 60 seconds",
                                "status": "timeout",
                            }

                    # Show progress during processing with essential logs
                    session_logs = get_session_logs()
                    analysis_status = ""
                    if session_logs:
                        latest_logs = (
                            session_logs[-3:] if len(session_logs) > 3 else session_logs
                        )
                        analysis_status = "\n" + "\n".join(
                            f"  {log}" for log in latest_logs
                        )

                    yield (
                        response_text
                        + f"\n\n🔧 **Direct scheduling call for: {task_description}**\n⏳ *Analyzing calendar and generating tasks...*{analysis_status}",
                        constraint_analysis_text,
                    )

                    try:
                        result = call_with_timeout()
                    except Exception as timeout_err:
                        logger.error(
                            f"MCP scheduling tool timed out or failed: {timeout_err}"
                        )
                        tool_response = f"\n\n⏰ **Scheduling timed out** - The request took longer than expected. Please try with a simpler task description."
                        response_text += tool_response
                        logger.info("Added timeout message to response")
                        yield (response_text, constraint_analysis_text)
                    else:
                        # Show progress for result processing
                        yield (
                            response_text
                            + f"\n\n🔧 **Direct scheduling call for: {task_description}**\n⏳ *Processing results...*",
                            constraint_analysis_text,
                        )

                        logger.info(
                            f"MCP tool completed with status: {result.get('status', 'unknown')}"
                        )
                        logger.info(f"MCP result type: {type(result)}")
                        logger.info(
                            f"MCP result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}"
                        )

                        # Debug the result structure
                        if isinstance(result, dict):
                            logger.info(f"Result status: {result.get('status')}")
                            logger.info(f"Result has schedule: {'schedule' in result}")
                            logger.info(
                                f"Result has calendar_entries: {'calendar_entries' in result}"
                            )
                            if "schedule" in result:
                                logger.info(
                                    f"Schedule length: {len(result.get('schedule', []))}"
                                )
                            if "calendar_entries" in result:
                                logger.info(
                                    f"Calendar entries length: {len(result.get('calendar_entries', []))}"
                                )

                        # Check multiple possible success conditions
                        is_success = False
                        success_msg = ""

                        if result.get("status") == "success":
                            is_success = True
                            success_msg = "Status is 'success'"
                        elif isinstance(result, dict) and "schedule" in result:
                            is_success = True
                            success_msg = "Result contains schedule data"
                        elif isinstance(result, dict) and len(result) > 0:
                            is_success = True
                            success_msg = "Result contains data"

                        logger.info(f"Success check: {is_success} ({success_msg})")

                        if is_success:
                            logger.info(
                                "SUCCESS CONDITION MET - Processing successful result"
                            )
                            schedule = result.get("schedule", [])
                            calendar_entries = result.get("calendar_entries", [])

                            # Sort the schedule by start time
                            schedule = sorted(schedule, key=lambda x: x.get("Start"))

                            # Format the schedule as a table
                            if schedule:
                                # Create table header
                                table_md = "\n\n## 📅 **Generated Schedule**\n\n"
                                table_md += "| Start Time | End Time | Task | Project | Employee | Duration | Skill | Status |\n"
                                table_md += "|------------|----------|------|---------|----------|----------|-------|--------|\n"

                                # Add table rows
                                for item in schedule:
                                    # Use the correct field names from schedule_to_dataframe
                                    start_time = item.get(
                                        "Start", item.get("start_time", "N/A")
                                    )
                                    end_time = item.get(
                                        "End", item.get("end_time", "N/A")
                                    )
                                    task_name = item.get(
                                        "Task",
                                        item.get(
                                            "task_name", item.get("description", "N/A")
                                        ),
                                    )
                                    project = item.get(
                                        "Project", item.get("project", "N/A")
                                    )
                                    employee = item.get(
                                        "Employee", item.get("employee", "N/A")
                                    )
                                    duration = item.get(
                                        "Duration (hours)", item.get("duration", "N/A")
                                    )
                                    skill = item.get(
                                        "Required Skill", item.get("skill", "N/A")
                                    )

                                    # Status indicators based on flags
                                    status_flags = []
                                    if item.get("Pinned", False):
                                        status_flags.append("📌 Pinned")
                                    if item.get("Unavailable", False):
                                        status_flags.append("⚠️ Unavailable")
                                    if item.get("Undesired", False):
                                        status_flags.append("😐 Undesired")
                                    if item.get("Desired", False):
                                        status_flags.append("✅ Desired")

                                    status = (
                                        " ".join(status_flags)
                                        if status_flags
                                        else "⚪ Normal"
                                    )

                                    # Format dates/times if they are datetime strings
                                    if isinstance(start_time, str) and "T" in str(
                                        start_time
                                    ):
                                        try:
                                            from datetime import datetime

                                            dt = datetime.fromisoformat(
                                                str(start_time).replace("Z", "+00:00")
                                            )
                                            start_time = dt.strftime("%m/%d %H:%M")
                                        except:
                                            pass

                                    if isinstance(end_time, str) and "T" in str(
                                        end_time
                                    ):
                                        try:
                                            from datetime import datetime

                                            dt = datetime.fromisoformat(
                                                str(end_time).replace("Z", "+00:00")
                                            )
                                            end_time = dt.strftime("%m/%d %H:%M")
                                        except:
                                            pass

                                    # Truncate long task names for table display
                                    if len(str(task_name)) > 35:
                                        task_name = str(task_name)[:32] + "..."

                                    # Format duration
                                    if isinstance(duration, (int, float)):
                                        duration = f"{duration}h"

                                    table_md += f"| {start_time} | {end_time} | {task_name} | {project} | {employee} | {duration} | {skill} | {status} |\n"

                                table_md += f"\n**Summary:**\n"
                                table_md += f"- 📊 **Total Items:** {len(schedule)}\n"
                                table_md += f"- 📅 **Calendar Events:** {len(calendar_entries)}\n"
                                table_md += f"- ✅ **Status:** Successfully scheduled around existing commitments\n"

                                # Count different types of tasks
                                pinned_count = sum(
                                    1 for item in schedule if item.get("Pinned", False)
                                )
                                project_tasks = sum(
                                    1
                                    for item in schedule
                                    if item.get("Project") == "PROJECT"
                                )
                                existing_events = sum(
                                    1
                                    for item in schedule
                                    if item.get("Project") == "EXISTING"
                                )

                                table_md += f"- 📌 **Pinned Events:** {pinned_count}\n"
                                table_md += f"- 🆕 **New Tasks:** {project_tasks}\n"
                                table_md += (
                                    f"- 📅 **Existing Events:** {existing_events}\n"
                                )

                                # Add JSON data section for debugging
                                # Generate constraint analysis separately
                                constraint_analysis_text = create_constraint_analysis(
                                    result
                                )

                                table_md += f"\n\n<details>\n<summary>📋 **Raw JSON Data** (click to expand)</summary>\n\n"
                                table_md += "```json\n"
                                table_md += safe_json_dumps(result)
                                table_md += "\n```\n</details>\n"

                                tool_response = table_md
                            else:
                                tool_response = f"""

                                📅 **Schedule Generated Successfully!**

                                **Task:** {task_description}
                                **Calendar Events Processed:** {len(calendar_entries)}
                                **Total Scheduled Items:** {len(schedule)}

                                ⚠️ **No schedule items to display** - This may indicate the task was completed or no scheduling was needed.
                                """

                                # Generate constraint analysis separately for empty schedules
                                constraint_analysis_text = create_constraint_analysis(
                                    result
                                )

                                tool_response += f"""
                                **Raw Result:**
                                ```json
                                {safe_json_dumps(result, indent=2)[:1000]}
                                ```
                                """

                            response_text += tool_response
                            logger.info("Added success message with table to response")
                            yield (response_text, constraint_analysis_text)
                        else:
                            logger.warning(f"SUCCESS CONDITION NOT MET")
                            error_msg = result.get(
                                "error",
                                f"Unknown error - result: {safe_json_dumps(result)[:200]}",
                            )
                            tool_response = f"\n\n❌ **Scheduling Error:** {error_msg}"
                            response_text += tool_response
                            logger.info("Added error message to response")
                            yield (response_text, constraint_analysis_text)

                except Exception as e:
                    logger.error(f"Direct scheduling call failed: {e}")

                    logger.error(f"Full traceback: {traceback.format_exc()}")
                    tool_response = f"\n\n❌ **Scheduling failed:** {str(e)}"
                    response_text += tool_response
                    logger.info("Added exception message to response")
                    yield (response_text, constraint_analysis_text)

        # Always yield final response
        logger.info(f"Final yield: response length {len(response_text)}")
        yield (response_text, constraint_analysis_text)

    except Exception as e:
        logger.error(f"Error in chat response: {e}")

        logger.error(f"Full traceback: {traceback.format_exc()}")
        yield (
            f"Error: {str(e)}",
            "## 🧠 **Constraint Analysis**\n\n❌ **Error occurred during processing**",
        )
