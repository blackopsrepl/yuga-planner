import os, argparse
import gradio as gr

from utils.logging_config import setup_logging, get_logger

# Initialize logging early - will be reconfigured based on debug mode
setup_logging()
logger = get_logger(__name__)

from utils.load_secrets import load_secrets

if not os.getenv("NEBIUS_API_KEY") or not os.getenv("NEBIUS_MODEL"):
    load_secrets("tests/secrets/creds.py")


# from handlers.web_backend import (
#     load_data,
#     show_solved,
#     start_timer,
#     auto_poll,
#     show_mock_project_content,
# )

from handlers.mcp_backend import process_message_and_attached_file

from services import MockProjectService

# Store last chat message and file in global variables (for demo purposes)
last_message_body = None
last_attached_file = None


# =========================
#           APP
# =========================


def app(debug: bool = False):
    """Main application function with optional debug mode"""

    # Configure logging based on debug mode
    if debug:
        os.environ["YUGA_DEBUG"] = "true"
        setup_logging("DEBUG")
        logger.info("Application started in DEBUG mode")
    else:
        os.environ["YUGA_DEBUG"] = "false"
        setup_logging("INFO")
        logger.info("Application started in normal mode")

    with gr.Blocks() as demo:
        gr.Markdown(
            """
            # 🐍 Yuga Planner

            **Yuga Planner** is a neuro-symbolic system that combines AI agents with constraint optimization
            for intelligent scheduling.

            ## 🔌 **Using as MCP Tool**

            You can use Yuga Planner as an MCP server to integrate scheduling into your AI workflows.
            """
        )

        _draw_info_page(debug)

        # Register the MCP tool as an API endpoint
        gr.api(process_message_and_attached_file)

    return demo


def _draw_info_page(debug: bool = False):
    with gr.Tab("📋 Information"):

        def get_server_url():
            try:
                return gr.get_state().server_url + "/gradio_api/mcp/sse"
            except:
                return "http://localhost:7860/gradio_api/mcp/sse"

        gr.Textbox(
            value=get_server_url(),
            label="🌐 MCP Server Endpoint",
            interactive=False,
            max_lines=1,
        )

        with gr.Accordion("📝 MCP Setup Instructions", open=True):
            gr.Markdown(
                """
                ### 1. **Cursor Setup Instructions (should work from any MCP client!)**

                **For Cursor AI Editor:**
                1. Create or edit your MCP configuration file: `~/.cursor/mcp.json`
                2. Add the yuga-planner server configuration:
                ```json
                {
                  "mcpServers": {
                    "yuga-planner": {
                      "url": -> "Insert the above endpoint URL here"
                    }
                  }
                }
                ```
                3. If you already have other MCP servers, add `yuga-planner` to the existing `mcpServers` object
                4. Restart Cursor to load the new configuration
                5. The tool will be available in your chat

                ### 2. **Usage Example**
                """
            )

            gr.Textbox(
                value="""use yuga-planner mcp tool
Task Description: Create a new EC2 instance on AWS

[Attach your calendar.ics file to provide existing commitments]

Tool Response: Optimized schedule created - EC2 setup task assigned to
available time slots around your existing meetings
[Returns JSON response with schedule data]

User: show all fields as a table, ordered by start date

[Displays formatted schedule table with all tasks and calendar events]""",
                label="💬 Cursor Chat Usage Example",
                interactive=False,
                lines=10,
            )

            gr.Markdown(
                """
                ### 3. **What it does**

                **Personal Task Scheduling with Calendar Integration:**

                1. 📅 **Parses your calendar** (.ics file) for existing commitments
                2. 🤖 **AI breaks down your task** into actionable subtasks using LLamaIndex + Nebius AI
                3. ⚡ **Constraint-based optimization** finds optimal time slots around your existing schedule
                4. 📋 **Returns complete solved schedule** integrated with your personal calendar events
                5. 🕘 **Respects business hours** (9:00-18:00) and excludes weekends automatically
                6. 📊 **JSON response format** - Ask to "show all fields as a table, ordered by start date" for readable formatting

                **Designed for**: Personal productivity and task planning around existing appointments in Cursor.
                """
            )

        if debug:
            with gr.Tab("🐛 Debug Info"):
                gr.Markdown(
                    """
                    # 🐛 Debug Information

                    **Debug Mode Enabled** - Additional system information and controls available.
                    """
                )

                with gr.Accordion("🔧 **Environment Details**", open=True):
                    import os

                    env_info = f"""
                    **🐍 Python Environment**
                    - Debug Mode: {debug}
                    - YUGA_DEBUG: {os.getenv('YUGA_DEBUG', 'Not Set')}
                    - Nebius API Key: {'✅ Set' if os.getenv('NEBIUS_API_KEY') else '❌ Not Set'}
                    - Nebius Model: {os.getenv('NEBIUS_MODEL', 'Not Set')}

                    **🌐 Server Information**
                    - MCP Endpoint: {get_server_url()}
                    - Current Working Directory: {os.getcwd()}
                    """
                    gr.Markdown(env_info)

                with gr.Accordion("📊 **System Status**", open=False):
                    gr.Markdown(
                        """
                        **🔄 Service Status**
                        - DataService: ✅ Active
                        - ScheduleService: ✅ Active
                        - StateService: ✅ Active
                        - LoggingService: ✅ Active
                        - MockProjectService: ✅ Active

                        **🔌 Integration Status**
                        - MCP Server: ✅ Enabled
                        - Gradio API: ✅ Active
                        - Real-time Logs: ✅ Streaming
                        """
                    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Yuga Planner - Team Scheduling Application"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with additional UI controls and logging",
    )
    parser.add_argument(
        "--server-name",
        default="0.0.0.0",
        help="Server name/IP to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--server-port",
        type=int,
        default=7860,
        help="Server port to bind to (default: 7860)",
    )

    args = parser.parse_args()

    app(debug=args.debug).launch(
        server_name=args.server_name, server_port=args.server_port, mcp_server=True
    )
