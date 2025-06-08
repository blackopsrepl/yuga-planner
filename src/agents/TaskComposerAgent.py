import os, asyncio, logging
from typing import Optional

from llama_index.llms.nebius import NebiusLLM
from llama_index.core.prompts import RichPromptTemplate
from llama_index.core.workflow import (
    StartEvent,
    StopEvent,
    Workflow,
    step,
    Event,
)

from utils.markdown_analyzer import MarkdownAnalyzer
from agents.task_processing import (
    remove_markdown_code_blocks,
    unwrap_tasks_from_generated,
    log_task_duration_breakdown,
    log_total_time,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

### MODEL SETTINGS ###
NEBIUS_API_KEY: str = os.getenv("NEBIUS_API_KEY", "")
NEBIUS_MODEL: str = os.getenv("NEBIUS_MODEL", "")

if not NEBIUS_MODEL or not NEBIUS_API_KEY:
    raise ValueError(
        "NEBIUS_MODEL and NEBIUS_API_KEY environment variables must be set"
    )

### PROMPT TEMPLATES ###
TASK_SPLITTER_PROMPT: str = "Split the following task into an accurate and concise tree of required subtasks:\n{{query}}\n\nYour output must be a markdown bullet list, with no additional comments.\n\n"
TASK_EVALUATOR_PROMPT: str = "Evaluate the elapsed time, in 30 minute units, for a competent human to complete the following task:\n{{query}}\n\nYour output must be a one integer, with no additional comments.\n\n"


class TaskComposerAgent:
    def __init__(self):
        self.llm: Optional[NebiusLLM] = None
        self.task_splitter_template: Optional[RichPromptTemplate] = None
        self.task_evaluator_template: Optional[RichPromptTemplate] = None
        self.workflow: Optional[TaskComposerWorkflow] = None

        self.set_llm()
        self.set_prompt_templates()
        self.set_workflow()

    def set_llm(self) -> None:
        self.llm = NebiusLLM(
            model=NEBIUS_MODEL,
            api_key=NEBIUS_API_KEY,
            timeout=30,
            max_retries=3,
            verify_ssl=True,
            request_timeout=30,
            max_tokens=1024,
            temperature=0.1,
        )

    def set_prompt_templates(self) -> None:
        input_map = {"query_str": "query"}
        self.task_splitter_template = RichPromptTemplate(
            TASK_SPLITTER_PROMPT, template_var_mappings=input_map
        )
        self.task_evaluator_template = RichPromptTemplate(
            TASK_EVALUATOR_PROMPT, template_var_mappings=input_map
        )

    def set_workflow(self) -> None:
        self.workflow = TaskComposerWorkflow(
            llm=self.llm,
            task_splitter_template=self.task_splitter_template,
            task_evaluator_template=self.task_evaluator_template,
            timeout=60,
            verbose=True,
        )

    async def run_workflow(self, query: str) -> str:
        result = await self.workflow.run(input=query)
        return result


class TaskSplitter(Event):
    task_splitter_output: str


class TaskEvaluator(Event):
    task_evaluator_output: list[tuple[str, str]]


class TaskComposerWorkflow(Workflow):
    def __init__(
        self,
        llm: NebiusLLM,
        task_splitter_template: RichPromptTemplate,
        task_evaluator_template: RichPromptTemplate,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._llm = llm
        self._task_splitter_template = task_splitter_template
        self._task_evaluator_template = task_evaluator_template

    @step
    async def step_one(self, event: StartEvent) -> TaskSplitter:
        logger.info("=== Step 1: Task Breakdown ===")
        logger.info(f"Input task: {event.input}")

        formatted_prompt = self._task_splitter_template.format(query=event.input)
        response = await asyncio.wait_for(
            asyncio.to_thread(self._llm.complete, formatted_prompt), timeout=30.0
        )

        logger.info("Task breakdown:")
        logger.info(response.text)
        return TaskSplitter(task_splitter_output=response.text)

    @step
    async def step_two(self, event: TaskSplitter) -> TaskEvaluator:
        logger.info("=== Step 2: Time Estimation ===")
        logger.info("Using task breakdown from Step 1:")
        logger.info(event.task_splitter_output)

        content = remove_markdown_code_blocks(event.task_splitter_output)

        analyzer = MarkdownAnalyzer(content)
        result = analyzer.identify_lists()["Unordered list"]
        tasks = unwrap_tasks_from_generated(result)

        merged_tasks = []
        for task in tasks:
            formatted_prompt = self._task_evaluator_template.format(query=task)
            response = await asyncio.wait_for(
                asyncio.to_thread(self._llm.complete, formatted_prompt), timeout=30.0
            )
            merged_tasks.append((task, response.text))

        log_task_duration_breakdown(merged_tasks)
        log_total_time(merged_tasks)

        return TaskEvaluator(task_evaluator_output=merged_tasks)

    @step
    async def step_three(self, event: TaskEvaluator) -> StopEvent:
        logger.info("=== Step 3: Final Result ===")
        log_task_duration_breakdown(event.task_evaluator_output)
        log_total_time(event.task_evaluator_output)
        return StopEvent(result=event.task_evaluator_output)
