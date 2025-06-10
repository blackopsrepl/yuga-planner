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
)

from state import app_state


# =========================
#           APP
# =========================


def app(debug: bool = False):
    with gr.Blocks() as demo:
        gr.Markdown(
            """
            # Yuga Planner
            Yuga Planner is a neuro-symbolic system prototype: it provides an agent-powered team scheduling and task allocation platform build on [Gradio](https://gradio.app/).
            """
        )
        gr.Markdown("### SWE Team Task Scheduling Demo")

        file_upload = gr.File(
            label="Upload Project Files (Markdown)",
            file_types=[".md"],
            file_count="multiple",
            visible=True,
        )

        gr.Markdown(
            "Upload a project description in Markdown format, click 'Load Data' to parse, decompose, and estimate tasks. Click 'Solve' to generate an optimal schedule."
        )

        # State for LLM output, persists per session
        llm_output_state = gr.State(value=None)
        job_id_state = gr.State(value=None)
        status_text = gr.Textbox(label="Solver Status", interactive=False)

        with gr.Row():
            load_btn = gr.Button("Load Data")
            solve_btn = gr.Button("Solve")

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
        ]

        # Timer for polling (not related to state)
        timer = gr.Timer(2, active=False)
        timer.tick(auto_poll, inputs=[job_id_state, llm_output_state], outputs=outputs)

        # Use state as both input and output
        load_btn.click(
            load_data,
            inputs=[file_upload, llm_output_state],
            outputs=outputs,
            api_name="load_data",
        )

        solve_btn.click(
            show_solved, inputs=[llm_output_state, job_id_state], outputs=outputs
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
        server_name=args.server_name, server_port=args.server_port
    )
