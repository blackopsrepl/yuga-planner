import gradio as gr

from utils.logging_config import setup_logging, get_logger

# Initialize logging
setup_logging()
logger = get_logger(__name__)


def draw_info_page(debug: bool = False):
    with gr.Tab("📋 Use as MCP Tool"):

        gr.Markdown(
            """
            ## 🔌 **Using as MCP Tool**

            You can use Yuga Planner as an MCP server to integrate scheduling into your AI workflows.
            """
        )

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


def get_server_url():
    try:
        return gr.get_state().server_url + "/gradio_api/mcp/sse"
    except:
        return "https://blackopsrepl-yuga-planner.hf.space/gradio_api/mcp/sse"
