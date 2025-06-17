import os, argparse, logging
import gradio as gr

logging.basicConfig(level=logging.INFO)


from utils.load_secrets import load_secrets

if not os.getenv("NEBIUS_API_KEY") or not os.getenv("NEBIUS_MODEL"):
    load_secrets("tests/secrets/creds.py")


from handlers import (
    load_data,
    show_solved,
    start_timer,
    auto_poll,
    show_mock_project_content,
)

from mcp_handlers import process_message_and_attached_file

from services import MockProjectService

# Store last chat message and file in global variables (for demo purposes)
last_message_body = None
last_attached_file = None


# =========================
#           APP
# =========================


def app(debug: bool = False):
    with gr.Blocks() as demo:
        gr.Markdown(
            """
            # Yuga Planner
            Yuga Planner is a neuro-symbolic system prototype: it provides an agent-powered team scheduling and task allocation platform built on [Gradio](https://gradio.app/).
            """
        )

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

        with gr.Tab("Task Scheduling"):
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
            log_terminal = gr.Textbox(
                label="Processing Logs",
                interactive=False,
                lines=8,
                max_lines=15,
                show_copy_button=True,
                placeholder="Logs will appear here during data loading...",
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
                return await auto_poll(job_id, llm_output, debug=debug)

            # Timer for polling (not related to state)
            timer = gr.Timer(2, active=False)
            timer.tick(
                auto_poll_with_debug,
                inputs=[job_id_state, llm_output_state],
                outputs=outputs,
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

                def debug_set_state(state):
                    logging.info(f"DEBUG: Setting state to test_value")
                    return "Debug: State set!", "test_value"

                def debug_show_state(state):
                    logging.info(f"DEBUG: Current state is {state}")
                    return f"Debug: Current state: {state}", gr.update()

                debug_out = gr.Textbox(label="Debug Output")
                debug_set_btn = gr.Button("Debug Set State")
                debug_show_btn = gr.Button("Debug Show State")

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

            # Register the MCP tool as an API endpoint
            gr.api(process_message_and_attached_file)

    return demo


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
