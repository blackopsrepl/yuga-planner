import os, argparse
import gradio as gr

from utils.logging_config import setup_logging, get_logger

# Initialize logging early - will be reconfigured based on debug mode
setup_logging()
logger = get_logger(__name__)

from utils.load_secrets import load_secrets

if not os.getenv("NEBIUS_API_KEY") or not os.getenv("NEBIUS_MODEL"):
    load_secrets("tests/secrets/creds.py")


from handlers.web_backend import (
    load_data,
    show_solved,
    start_timer,
    auto_poll,
    show_mock_project_content,
)

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
            # Yuga Planner
            Yuga Planner is a neuro-symbolic system prototype: it provides an agent-powered team scheduling and task allocation platform built on [Gradio](https://gradio.app/).
            """
        )

        _draw_info_page(debug)
        # _draw_hackathon_page(debug)

        # Register the MCP tool as an API endpoint
        gr.api(process_message_and_attached_file)

    return demo


def _draw_info_page(debug: bool = False):
    with gr.Tab("Information"):

        def get_server_url():
            try:
                return gr.get_state().server_url + "/gradio_api/mcp/sse"
            except:
                return "http://localhost:7860/gradio_api/mcp/sse"

        gr.Markdown(
            f"""
            This is a demo of the Yuga Planner system.

            To use as an MCP server:
            1. Register the MCP server with your client using the URL:
            ```
            {get_server_url()}
            ```
            2. Call the tool from your client. Example:
            ```
            use yuga planner tool @tests/data/calendar.ics
            Task Description: Create a new AWS VPC
            ```

            """
        )


def _draw_hackathon_page(debug: bool = False):
    with gr.Tab("Hackathon Agent Demo"):
        gr.Markdown("### SWE Team Task Scheduling Demo")

        gr.Markdown(
            """
            ## Instructions
            1. Choose a project source - either upload your own project file(s) or select from our mock projects
            2. Click 'Load Data' to parse, decompose, and estimate tasks
            3. Click 'Solve' to generate an optimal schedule based on employee skills and availability
            4. Review the results in the tables below
            """
        )

        # Project source selector
        project_source = gr.Radio(
            choices=["Upload Project Files", "Use Mock Projects"],
            value="Upload Project Files",
            label="Project Source",
        )

        # Configuration parameters
        with gr.Row():
            employee_count = gr.Number(
                label="Number of Employees",
                value=12,
                minimum=1,
                maximum=100,
                step=1,
                precision=0,
            )
            days_in_schedule = gr.Number(
                label="Days in Schedule",
                value=365,
                minimum=1,
                maximum=365,
                step=1,
                precision=0,
            )

        # File upload component (initially visible)
        with gr.Group(visible=True) as file_upload_group:
            file_upload = gr.File(
                label="Upload Project Files (Markdown)",
                file_types=[".md"],
                file_count="multiple",
            )

        # Mock projects dropdown (initially hidden)
        with gr.Group(visible=False) as mock_projects_group:
            # Get mock project names from ProjectService
            available_projects = MockProjectService.get_available_project_names()
            mock_project_dropdown = gr.Dropdown(
                choices=available_projects,
                label="Select Mock Projects (multiple selection allowed)",
                value=[available_projects[0]] if available_projects else [],
                multiselect=True,
            )

            # Accordion for viewing mock project content
            with gr.Accordion("📋 Project Content Preview", open=False):
                mock_project_content_accordion = gr.Textbox(
                    label="Project Content",
                    interactive=False,
                    lines=15,
                    max_lines=20,
                    show_copy_button=True,
                    placeholder="Select projects above and expand this section to view content...",
                )

            # Auto-update content when projects change
            mock_project_dropdown.change(
                show_mock_project_content,
                inputs=[mock_project_dropdown],
                outputs=[mock_project_content_accordion],
            )

        # Log Terminal - Always visible for streaming logs
        gr.Markdown("## Live Log Terminal")

        # Show debug status
        if debug:
            gr.Markdown(
                "🐛 **Debug Mode Enabled** - Showing detailed logs including DEBUG messages"
            )
        else:
            gr.Markdown(
                "ℹ️ **Normal Mode** - Showing INFO, WARNING, and ERROR messages"
            )

        log_terminal = gr.Textbox(
            label="Processing Logs",
            interactive=False,
            lines=8,
            max_lines=15,
            show_copy_button=True,
            placeholder="Logs will appear here during data loading and solving...",
        )

        # Toggle visibility based on project source selection
        def toggle_visibility(choice):
            if choice == "Upload Project Files":
                return gr.update(visible=True), gr.update(visible=False)
            else:
                return gr.update(visible=False), gr.update(visible=True)

        project_source.change(
            toggle_visibility,
            inputs=[project_source],
            outputs=[file_upload_group, mock_projects_group],
        )

        # State for LLM output, persists per session
        llm_output_state = gr.State(value=None)
        job_id_state = gr.State(value=None)
        status_text = gr.Textbox(
            label="Solver Status",
            interactive=False,
            lines=8,
            max_lines=20,
            show_copy_button=True,
        )

        with gr.Row():
            load_btn = gr.Button("Load Data")
            solve_btn = gr.Button("Solve", interactive=False)  # Initially disabled

        gr.Markdown("## Employees")
        employees_table = gr.Dataframe(label="Employees", interactive=False)

        gr.Markdown("## Tasks")
        schedule_table = gr.Dataframe(label="Tasks Table", interactive=False)

        # Outputs: always keep state as last output
        outputs = [
            employees_table,
            schedule_table,
            job_id_state,
            status_text,
            llm_output_state,
            log_terminal,
        ]

        # Outputs for load_data that also enables solve button
        load_outputs = outputs + [solve_btn]

        # Create wrapper function to pass debug flag to auto_poll
        async def auto_poll_with_debug(job_id, llm_output):
            result = await auto_poll(job_id, llm_output, debug=debug)
            # auto_poll now returns 6 values including logs
            return result

        # Timer for polling (not related to state)
        timer = gr.Timer(2, active=False)
        timer.tick(
            auto_poll_with_debug,
            inputs=[job_id_state, llm_output_state],
            outputs=outputs,  # This now includes log_terminal updates
        )

        # Create wrapper function to pass debug flag to load_data
        async def load_data_with_debug(
            project_source,
            file_obj,
            mock_projects,
            employee_count,
            days_in_schedule,
            llm_output,
            progress=gr.Progress(),
        ):
            async for result in load_data(
                project_source,
                file_obj,
                mock_projects,
                employee_count,
                days_in_schedule,
                llm_output,
                debug=debug,
                progress=progress,
            ):
                yield result

        # Use state as both input and output
        load_btn.click(
            load_data_with_debug,
            inputs=[
                project_source,
                file_upload,
                mock_project_dropdown,
                employee_count,
                days_in_schedule,
                llm_output_state,
            ],
            outputs=load_outputs,
            api_name="load_data",
        )

        # Create wrapper function to pass debug flag to show_solved
        async def show_solved_with_debug(state_data, job_id):
            return await show_solved(state_data, job_id, debug=debug)

        solve_btn.click(
            show_solved_with_debug,
            inputs=[llm_output_state, job_id_state],
            outputs=outputs,
        ).then(start_timer, inputs=[job_id_state, llm_output_state], outputs=timer)

        if debug:
            gr.Markdown("### 🐛 Debug Controls")
            gr.Markdown(
                "These controls help test the centralized logging system and state management."
            )

            def debug_set_state(state):
                logger.info("DEBUG: Setting state to test_value")
                logger.debug("DEBUG: Detailed state operation in progress")
                return "Debug: State set!", "test_value"

            def debug_show_state(state):
                logger.info("DEBUG: Current state is %s", state)
                logger.debug("DEBUG: State retrieval operation completed")
                return f"Debug: Current state: {state}", gr.update()

            def debug_test_logging():
                """Test all logging levels for UI demonstration"""
                logger.debug("🐛 DEBUG: This is a debug message")
                logger.info("ℹ️ INFO: This is an info message")
                logger.warning("⚠️ WARNING: This is a warning message")
                logger.error("❌ ERROR: This is an error message")
                return "Generated test log messages at all levels"

            debug_out = gr.Textbox(label="Debug Output")

            with gr.Row():
                debug_set_btn = gr.Button("Debug Set State")
                debug_show_btn = gr.Button("Debug Show State")
                debug_log_btn = gr.Button("Test Log Levels")

            debug_set_btn.click(
                debug_set_state,
                inputs=[llm_output_state],
                outputs=[debug_out, llm_output_state],
            )
            debug_show_btn.click(
                debug_show_state,
                inputs=[llm_output_state],
                outputs=[debug_out, gr.State()],
            )
            debug_log_btn.click(
                debug_test_logging,
                inputs=[],
                outputs=[debug_out],
            )


def set_test_state():
    logger.debug("Setting state to test_value")
    app_state.set("test_key", "test_value")
    return "State set to test_value"


def get_test_state():
    state = app_state.get("test_key", "No state found")
    logger.debug("Current state is %s", state)
    return f"Current state: {state}"


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
