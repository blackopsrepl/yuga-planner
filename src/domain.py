import os
from dataclasses import dataclass


@dataclass
class AgentsConfig:
    """Global configuration for all agents"""

    # Model settings
    nebius_api_key: str
    nebius_model: str

    # Prompt templates
    task_splitter_prompt: str = "Split the following task into an accurate and concise tree of required subtasks:\n{{query}}\n\nYour output must be a markdown bullet list, with no additional comments.\n\n"
    task_evaluator_prompt: str = "Evaluate the elapsed time, in 30 minute units, for a competent human to complete the following task:\n{{query}}\n\nYour output must be a one integer, with no additional comments.\n\n"
    task_deps_matcher_prompt: str = "Given the following task:\n{{task}}\n\nAnd these available skills:\n{{skills}}\n\nIn this context:\n{{context}}\n\nSelect the most appropriate skill to complete this task. Return only the skill name as a string, with no additional comments or formatting.\n\n"

    # Mock projects
    MOCK_PROJECTS: dict[str, str] = {
        "go-rssagg": """GO-RSSAGG\n\nRSS aggregator backend written in Go. Features REST API and basic authentication""",
        "rust": """RUST PROJECT\n\nData Pipeline that extracts chess match metrics and match annotations from Excel files, using AWS Lambda and Step Functions and written in Rust""",
    }

    # LLM settings
    timeout: int = 30
    max_retries: int = 3
    verify_ssl: bool = True
    request_timeout: int = 30
    max_tokens: int = 1024
    temperature: float = 0.1

    def __post_init__(self):
        """Validate required configuration"""
        if not self.nebius_model or not self.nebius_api_key:
            if self.nebius_model == "dev-model" and self.nebius_api_key == "dev-key":
                # Development mode - just warn
                import warnings

                warnings.warn(
                    "Using development defaults for NEBIUS_MODEL and NEBIUS_API_KEY"
                )
            else:
                raise ValueError(
                    "NEBIUS_MODEL and NEBIUS_API_KEY environment variables must be set"
                )


# Global configuration instance
# For development environments where env vars might not be set, use defaults
AGENTS_CONFIG = AgentsConfig(
    nebius_api_key=os.getenv("NEBIUS_API_KEY", "dev-key"),
    nebius_model=os.getenv("NEBIUS_MODEL", "dev-model"),
)
