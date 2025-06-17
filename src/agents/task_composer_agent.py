import os, asyncio, logging
from typing import Optional, List

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
    remove_markdown_list_elements,
    unwrap_tasks_from_generated,
    log_task_duration_breakdown,
    log_total_time,
)

logging.basicConfig(level=logging.INFO)
logger: logging.Logger = logging.getLogger(__name__)


from domain import AgentsConfig, AGENTS_CONFIG


class TaskComposerAgent:
    def __init__(self, config: AgentsConfig = AGENTS_CONFIG):
        self.config = config
        self.llm: Optional[NebiusLLM] = None
        self.task_splitter_template: Optional[RichPromptTemplate] = None
        self.task_evaluator_template: Optional[RichPromptTemplate] = None
        self.task_deps_matcher_template: Optional[RichPromptTemplate] = None
        self.workflow: Optional[TaskComposerWorkflow] = None

        self.set_llm()
        self.set_prompt_templates()
        self.set_workflow()

    def set_llm(self) -> None:
        self.llm = NebiusLLM(
            model=self.config.nebius_model,
            api_key=self.config.nebius_api_key,
            timeout=self.config.timeout,
            max_retries=self.config.max_retries,
            verify_ssl=self.config.verify_ssl,
            request_timeout=self.config.request_timeout,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
        )

    def set_prompt_templates(self) -> None:
        self.task_splitter_template = RichPromptTemplate(
            self.config.task_splitter_prompt,
            template_var_mappings={"query_str": "query"},
        )
        self.task_evaluator_template = RichPromptTemplate(
            self.config.task_evaluator_prompt,
            template_var_mappings={"query_str": "query"},
        )
        self.task_deps_matcher_template = RichPromptTemplate(
            self.config.task_deps_matcher_prompt,
            template_var_mappings={
                "query_str": "task",
                "skills_str": "skills",
                "context_str": "context",
            },
        )

    def set_workflow(self) -> None:
        self.workflow = TaskComposerWorkflow(
            llm=self.llm,
            task_splitter_template=self.task_splitter_template,
            task_evaluator_template=self.task_evaluator_template,
            task_deps_matcher_template=self.task_deps_matcher_template,
            timeout=self.config.workflow_timeout,
            verbose=True,
        )

    async def run_workflow(
        self, query: str, skills: Optional[List[str]] = None, context: str = ""
    ) -> str:
        return await self.workflow.run(
            input=query, skills=skills or [], context=context
        )


class TaskSplitter(Event):
    task_splitter_output: str
    skills: List[str]
    context: str


class TaskEvaluator(Event):
    task_evaluator_output: list[tuple[str, str]]
    skills: List[str]
    context: str


class TaskDependencyMatcher(Event):
    task_dependency_output: list[
        tuple[str, str, str]
    ]  # (task, duration, matched_skill)


class TaskComposerWorkflow(Workflow):
    def __init__(
        self,
        llm: NebiusLLM,
        task_splitter_template: RichPromptTemplate,
        task_evaluator_template: RichPromptTemplate,
        task_deps_matcher_template: RichPromptTemplate,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._llm = llm
        self._task_splitter_template = task_splitter_template
        self._task_evaluator_template = task_evaluator_template
        self._task_deps_matcher_template = task_deps_matcher_template

    @step
    async def split_tasks(self, event: StartEvent) -> TaskSplitter:
        logger.info("=== Step 1: Task Breakdown ===")
        logger.info(f"Input task: {event.input}")

        formatted_prompt: str = self._task_splitter_template.format(query=event.input)

        response = await asyncio.wait_for(
            asyncio.to_thread(self._llm.complete, formatted_prompt), timeout=30.0
        )

        logger.info("Task breakdown:")
        logger.info(response.text)

        # Get skills and context from the event, default to empty if not provided
        skills = getattr(event, "skills", [])
        context = getattr(event, "context", "")

        logger.info(f"Received skills: {skills}")
        logger.info(f"Received context: {context}")

        return TaskSplitter(
            task_splitter_output=response.text, skills=skills, context=context
        )

    @step
    async def evaluate_tasks_duration(self, event: TaskSplitter) -> TaskEvaluator:
        logger.info("=== Step 2: Time Estimation ===")
        logger.info("Using task breakdown from Step 1:")
        logger.info(event.task_splitter_output)

        content: str = remove_markdown_code_blocks(event.task_splitter_output)
        analyzer: MarkdownAnalyzer = MarkdownAnalyzer(content)
        result: list = analyzer.identify_lists()["Unordered list"]
        tasks: list[str] = unwrap_tasks_from_generated(result)

        logger.info(f"Processing {len(tasks)} tasks for time estimation...")

        merged_tasks: list[tuple[str, str]] = []
        for i, task in enumerate(tasks, 1):
            try:
                formatted_prompt: str = self._task_evaluator_template.format(query=task)

                response = await asyncio.wait_for(
                    asyncio.to_thread(self._llm.complete, formatted_prompt),
                    timeout=30.0,
                )
                merged_tasks.append((task, response.text))
                logger.info(f"Completed time estimation {i}/{len(tasks)}")

            except asyncio.TimeoutError:
                logger.warning(f"Time estimation timeout for task {i}: {task[:50]}...")

                # Use default duration of 2 units (1 hour)
                merged_tasks.append((task, "2"))

            except Exception as e:
                logger.error(f"Error estimating time for task {i}: {e}")

                # Use default duration of 2 units (1 hour)
                merged_tasks.append((task, "2"))

        # remove markdown list elements wrapped in **
        merged_tasks = remove_markdown_list_elements(merged_tasks)
        log_task_duration_breakdown(merged_tasks)
        log_total_time(merged_tasks)

        return TaskEvaluator(
            task_evaluator_output=merged_tasks,
            skills=event.skills,
            context=event.context,
        )

    @step
    async def evaluate_tasks_dependencies(
        self, event: TaskEvaluator
    ) -> TaskDependencyMatcher:
        logger.info("=== Step 3: Task Dependencies ===")
        logger.info("Matching tasks with available skills")

        # Get skills and context from the event
        skills = event.skills
        context = event.context

        if not skills:
            logger.warning("No skills provided, skipping dependency matching")
            # Convert to dependency format with empty skill
            task_dependencies = [
                (task, duration, "") for task, duration in event.task_evaluator_output
            ]
            return TaskDependencyMatcher(task_dependency_output=task_dependencies)

        skills_str = "\n".join([f"- {skill}" for skill in skills])
        logger.info(f"Available skills: {skills}")
        logger.info(f"Context: {context}")

        task_dependencies: list[tuple[str, str, str]] = []
        logger.info(
            f"Processing {len(event.task_evaluator_output)} tasks for skill matching..."
        )

        for i, (task, duration) in enumerate(event.task_evaluator_output, 1):
            try:
                formatted_prompt: str = self._task_deps_matcher_template.format(
                    task=task, skills=skills_str, context=context
                )

                response = await asyncio.wait_for(
                    asyncio.to_thread(self._llm.complete, formatted_prompt),
                    timeout=30.0,
                )

                matched_skill = response.text.strip()
                task_dependencies.append((task, duration, matched_skill))
                logger.info(
                    f"Completed skill matching {i}/{len(event.task_evaluator_output)}: {task[:50]}... -> {matched_skill}"
                )

            except asyncio.TimeoutError:
                logger.warning(f"Skill matching timeout for task {i}: {task[:50]}...")

                # Use first available skill as fallback
                fallback_skill = skills[0] if skills else ""
                task_dependencies.append((task, duration, fallback_skill))

            except Exception as e:
                logger.error(f"Error matching skill for task {i}: {e}")

                # Use first available skill as fallback
                fallback_skill = skills[0] if skills else ""
                task_dependencies.append((task, duration, fallback_skill))

        return TaskDependencyMatcher(task_dependency_output=task_dependencies)

    @step
    async def result_output(self, event: TaskDependencyMatcher) -> StopEvent:
        logger.info("=== Step 4: Final Result ===")

        # Log the final breakdown with dependencies
        for task, duration, skill in event.task_dependency_output:
            logger.info(f"Task: {task}")
            logger.info(f"  Duration: {duration} units")
            logger.info(f"  Matched Skill: {skill}")
            logger.info("-" * 50)

        return StopEvent(result=event.task_dependency_output)
