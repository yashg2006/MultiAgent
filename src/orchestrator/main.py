"""
Main Pipeline Orchestrator module.
Coordinates agent workflows, task distribution, and state progression.
"""

from __future__ import annotations

import time
import uuid

from src.agents.base import Agent
from src.agents.planner_agent.agent import PlannerAgent
from src.agents.research_agent.agent import ResearchAgent
from src.agents.validator_agent.agent import ValidatorAgent
from src.shared.config import settings
from src.shared.schemas import AgentRequest, AgentResponse, RunResult, RunStep, ValidationStatus
from src.shared.utils import setup_logger

logger = setup_logger(__name__)


class Orchestrator:
    """
    Coordinates Planner -> Research (per sub-task) -> Validator, with retry
    on validation failure up to `max_retries`, per the architecture in
    docs/architecture_design.md.

    New agent types can be added by passing a differently-keyed `agents`
    dict at construction time; no change to this class is required (NFR-02).
    """

    def __init__(
        self,
        agents: dict[str, Agent] | None = None,
        max_retries: int | None = None,
    ) -> None:
        self.agents: dict[str, Agent] = agents or {
            "planner": PlannerAgent(),
            "research": ResearchAgent(),
            "validator": ValidatorAgent(),
        }
        self.max_retries = max_retries if max_retries is not None else settings.max_retries
        self.state: dict = {}

    def run(self, input_task: str) -> RunResult:
        """
        Execute the full multi-agent pipeline for `input_task` and return a
        RunResult with the final status, result/error, and a step trace.
        """
        task_id = str(uuid.uuid4())
        steps: list[RunStep] = []

        if not input_task or not input_task.strip():
            return RunResult(
                task_id=task_id,
                status="error",
                error="input_task must not be empty.",
            )

        plan_response, plan_step = self._dispatch(
            "planner", AgentRequest(task_id=task_id, prompt=input_task)
        )
        steps.append(plan_step)
        if plan_response.status != "success" or plan_response.result is None:
            return RunResult(
                task_id=task_id,
                status="error",
                error=plan_response.error or "Planner failed to produce a plan.",
                steps=steps,
            )

        sub_tasks = plan_response.result["plan"]["sub_tasks"]

        attempt = 0
        last_aggregated: dict = {}
        last_validation_reasons: list[str] = []
        while attempt < self.max_retries:
            attempt += 1
            aggregated, research_steps = self._run_research(task_id, sub_tasks)
            steps.extend(research_steps)
            last_aggregated = aggregated

            validator_response, validator_step = self._dispatch(
                "validator",
                AgentRequest(
                    task_id=task_id,
                    prompt="validate aggregated research results",
                    metadata={"results": aggregated},
                ),
            )
            steps.append(validator_step)

            if validator_response.status == "success" and validator_response.result:
                validation = validator_response.result["validation"]
                if validation["status"] == ValidationStatus.PASS.value:
                    return RunResult(
                        task_id=task_id,
                        status="success",
                        result=aggregated,
                        steps=steps,
                        retries_used=attempt - 1,
                    )
                last_validation_reasons = validation.get("reasons", [])
            else:
                last_validation_reasons = [validator_response.error or "validator error"]

            logger.warning(
                "Validation failed on attempt %d/%d for task_id=%s: %s",
                attempt,
                self.max_retries,
                task_id,
                last_validation_reasons,
            )

        return RunResult(
            task_id=task_id,
            status="partial",
            result=last_aggregated,
            error=f"Validation failed after {self.max_retries} attempt(s): "
            f"{'; '.join(last_validation_reasons)}",
            steps=steps,
            retries_used=self.max_retries,
        )

    def _run_research(self, task_id: str, sub_tasks: list[dict]) -> tuple[dict, list[RunStep]]:
        """Dispatch the Research Agent for each sub-task and aggregate results."""
        aggregated: dict = {}
        steps: list[RunStep] = []
        for sub_task in sub_tasks:
            response, step = self._dispatch(
                "research",
                AgentRequest(task_id=task_id, prompt=sub_task["description"]),
            )
            steps.append(step)
            if response.status == "success" and response.result is not None:
                aggregated[sub_task["id"]] = response.result
            else:
                aggregated[sub_task["id"]] = {"error": response.error or "research failed"}
        return aggregated, steps

    def _dispatch(self, agent_key: str, request: AgentRequest) -> tuple[AgentResponse, RunStep]:
        """Invoke a registered agent by key, timing and tracing the call."""
        agent = self.agents[agent_key]
        start = time.monotonic()
        try:
            response = agent.execute(request)
            status = response.status
            detail = {"error": response.error} if response.error else None
        except Exception as exc:  # noqa: BLE001 - a crashing agent must not crash the orchestrator
            logger.exception("Agent '%s' raised during execute()", agent_key)
            response = AgentResponse(task_id=request.task_id, status="error", error=str(exc))
            status = "error"
            detail = {"error": str(exc)}
        latency = time.monotonic() - start
        step = RunStep(
            step_name=agent_key,
            status=status,
            latency_seconds=latency,
            detail=detail,
        )
        return response, step
