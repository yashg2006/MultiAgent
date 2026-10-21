"""
Main Pipeline Orchestrator module.
Coordinates agent workflows, task distribution, and state progression.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from src.agents.base import Agent
from src.agents.planner_agent.agent import PlannerAgent
from src.agents.research_agent.agent import ResearchAgent
from src.agents.validator_agent.agent import ValidatorAgent
from src.shared.config import settings
from src.shared.schemas import (
    AgentRequest,
    AgentResponse,
    LLMUsage,
    RunResult,
    RunStep,
    ValidationStatus,
)
from src.shared.utils import setup_logger

logger = setup_logger(__name__)

StepCallback = Callable[[RunStep], None]
CancelCheck = Callable[[], bool]


def dependency_levels(sub_tasks: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Group sub-tasks into levels: each level depends only on earlier levels,
    so everything within a level can run in parallel. Order within a level
    follows the plan. Unknown dependencies are ignored; if a cycle slips
    through, the remaining sub-tasks form one final level rather than hanging."""
    ids = {s["id"] for s in sub_tasks}
    pending = {s["id"]: {d for d in s.get("depends_on", []) if d in ids} for s in sub_tasks}
    by_id = {s["id"]: s for s in sub_tasks}
    levels: list[list[dict[str, Any]]] = []
    while pending:
        ready = [i for i in by_id if i in pending and not pending[i]]
        if not ready:
            logger.warning("Dependency cycle among %s; running them together", sorted(pending))
            ready = [i for i in by_id if i in pending]
        levels.append([by_id[i] for i in ready])
        for i in ready:
            del pending[i]
        for deps in pending.values():
            deps.difference_update(ready)
    return levels


class Orchestrator:
    """
    Coordinates Planner -> Research (per sub-task, parallel where independent)
    -> Validator, retrying the Research->Validate cycle on rejection up to
    `max_retries` times, per docs/architecture_design.md.

    New agent types can be added by passing a differently-keyed `agents`
    dict at construction time; no change to this class is required (NFR-02).
    """

    def __init__(
        self,
        agents: dict[str, Agent] | None = None,
        max_retries: int | None = None,
        max_parallel: int | None = None,
    ) -> None:
        self.agents: dict[str, Agent] = agents or {
            "planner": PlannerAgent(),
            "research": ResearchAgent(),
            "validator": ValidatorAgent(),
        }
        self.max_retries = max_retries if max_retries is not None else settings.max_retries
        self.max_parallel = max_parallel or settings.max_parallel_research
        self.state: dict = {}

    def run(
        self,
        input_task: str,
        *,
        task_id: str | None = None,
        on_step: StepCallback | None = None,
        should_cancel: CancelCheck | None = None,
    ) -> RunResult:
        """
        Execute the full pipeline for `input_task`.

        Args:
            task_id: id to use for the run (e.g. the API's task id); generated
                if not given.
            on_step: called with each RunStep as soon as it finishes, e.g. to
                stream progress. Errors in the callback are logged, not raised.
            should_cancel: polled between stages; when it returns True the run
                stops and returns status "cancelled" with whatever it has.
        """
        task_id = task_id or str(uuid.uuid4())
        steps: list[RunStep] = []

        def emit(step: RunStep) -> None:
            steps.append(step)
            if on_step is not None:
                try:
                    on_step(step)
                except Exception:  # noqa: BLE001 - observers must not break runs
                    logger.exception("on_step callback failed for task_id=%s", task_id)

        def cancelled() -> bool:
            return should_cancel is not None and should_cancel()

        def finish(status: str, **fields: Any) -> RunResult:
            total = sum((s.usage for s in steps), LLMUsage())
            return RunResult(task_id=task_id, status=status, steps=steps, usage=total, **fields)

        if not input_task or not input_task.strip():
            return finish("error", error="input_task must not be empty.")

        plan_response, plan_step = self._dispatch(
            "planner", AgentRequest(task_id=task_id, prompt=input_task)
        )
        emit(plan_step)
        if plan_response.status != "success" or plan_response.result is None:
            return finish("error", error=plan_response.error or "Planner failed to produce a plan.")

        sub_tasks = plan_response.result["plan"]["sub_tasks"]
        levels = dependency_levels(sub_tasks)

        last_aggregated: dict = {}
        last_validation_reasons: list[str] = []
        for attempt in range(1, self.max_retries + 1):
            feedback = last_validation_reasons if attempt > 1 else []
            aggregated: dict = {}
            for level in levels:
                if cancelled():
                    return finish(
                        "cancelled",
                        result=last_aggregated or aggregated or None,
                        error="Cancelled by user.",
                        retries_used=attempt - 1,
                    )
                for sub_task, response, step in self._run_level(
                    task_id, level, aggregated, feedback
                ):
                    emit(step)
                    if response.status == "success" and response.result is not None:
                        aggregated[sub_task["id"]] = response.result
                    else:
                        aggregated[sub_task["id"]] = {"error": response.error or "research failed"}
            last_aggregated = aggregated

            if cancelled():
                return finish(
                    "cancelled",
                    result=aggregated,
                    error="Cancelled by user.",
                    retries_used=attempt - 1,
                )

            validator_response, validator_step = self._dispatch(
                "validator",
                AgentRequest(
                    task_id=task_id,
                    prompt="validate aggregated research results",
                    metadata={"results": aggregated, "objective": input_task},
                ),
            )
            emit(validator_step)

            # The Validator returns status="success" when validation passed,
            # "rejected" when it ran but the result failed (reasons are still in
            # `result`), or "error" if it couldn't run at all (no `result`).
            if validator_response.result is not None:
                validation = validator_response.result["validation"]
                if (
                    validator_response.status == "success"
                    and validation["status"] == ValidationStatus.PASS.value
                ):
                    return finish("success", result=aggregated, retries_used=attempt - 1)
                last_validation_reasons = validation.get("reasons") or ["validation failed"]
            else:
                last_validation_reasons = [validator_response.error or "validator error"]

            logger.warning(
                "Validation failed on attempt %d/%d for task_id=%s: %s",
                attempt,
                self.max_retries,
                task_id,
                last_validation_reasons,
            )

        return finish(
            "partial",
            result=last_aggregated,
            error=f"Validation failed after {self.max_retries} attempt(s): "
            f"{'; '.join(last_validation_reasons)}",
            retries_used=self.max_retries,
        )

    def _run_level(
        self,
        task_id: str,
        level: list[dict[str, Any]],
        aggregated: dict[str, Any],
        feedback: list[str],
    ) -> list[tuple[dict[str, Any], AgentResponse, RunStep]]:
        """Research every sub-task in one dependency level, in parallel when
        there's more than one. Results come back in plan order."""
        requests = []
        for sub_task in level:
            context = {
                dep: str(aggregated[dep].get("findings", ""))
                for dep in sub_task.get("depends_on", [])
                if isinstance(aggregated.get(dep), dict) and aggregated[dep].get("findings")
            }
            metadata: dict[str, Any] = {"sub_task_id": sub_task["id"]}
            if context:
                metadata["context"] = context
            if feedback:
                metadata["feedback"] = feedback
            requests.append(
                AgentRequest(task_id=task_id, prompt=sub_task["description"], metadata=metadata)
            )

        if len(requests) == 1:
            outcomes = [self._dispatch("research", requests[0])]
        else:
            with ThreadPoolExecutor(max_workers=min(self.max_parallel, len(requests))) as pool:
                outcomes = list(pool.map(lambda r: self._dispatch("research", r), requests))

        results = []
        for sub_task, (response, step) in zip(level, outcomes):
            step.sub_task_id = sub_task["id"]
            results.append((sub_task, response, step))
        return results

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
            usage=response.usage or LLMUsage(),
        )
        return response, step
