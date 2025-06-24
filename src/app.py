import os, argparse
import gradio as gr

from utils.logging_config import setup_logging, get_logger
from utils.version import __version__

# Initialize logging early - will be reconfigured based on debug mode
setup_logging()
logger = get_logger(__name__)

from handlers.mcp_backend import process_message_and_attached_file
from ui.pages.chat import draw_chat_page


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
            """
        )

        draw_chat_page(debug)

        # Version footer
        gr.Markdown(
            f"""
            <div style="text-align: center; margin-top: 2rem; padding: 1rem; color: #666; font-size: 0.8rem;">
                Yuga Planner v{__version__}
            </div>
            """,
            elem_classes=["version-footer"],
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
