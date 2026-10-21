"""
Planner Agent implementation.
Responsible for breaking down high-level objectives into executable sub-tasks.
"""

from __future__ import annotations

from pydantic import ValidationError

from src.agents.base import Agent
from src.shared.config import settings
from src.shared.llm_provider import extract_json_object
from src.shared.schemas import AgentRequest, AgentResponse, LLMUsage, Plan, SubTask
from src.shared.utils import setup_logger

logger = setup_logger(__name__)

_SYSTEM_PROMPT = (
    "You are a planning assistant. Break the user's objective into concrete, "
    "self-contained research questions that together cover it.\n"
    "Respond with ONLY a JSON object, no prose, in exactly this shape:\n"
    '{"sub_tasks": [{"id": "st-1", "description": "...", "depends_on": []}]}\n'
    "Rules: ids are st-1, st-2, ... in order; each description is one specific "
    "question; depends_on lists the ids whose answers are needed first (use [] when "
    "a sub-task is independent, so it can run in parallel); no circular dependencies."
)


class PlanError(ValueError):
    """The model's output could not be turned into a valid plan."""


def validate_plan_structure(sub_tasks: list[SubTask], max_sub_tasks: int) -> None:
    """Check ids are unique, dependencies exist, and there are no cycles.

    Raises PlanError with a message the model can act on in a repair attempt.
    """
    if not sub_tasks:
        raise PlanError("The plan has no sub-tasks.")
    if len(sub_tasks) > max_sub_tasks:
        raise PlanError(f"The plan has {len(sub_tasks)} sub-tasks; the limit is {max_sub_tasks}.")
    ids = [s.id for s in sub_tasks]
    if len(set(ids)) != len(ids):
        raise PlanError("Sub-task ids must be unique.")
    known = set(ids)
    for sub in sub_tasks:
        if not sub.description.strip():
            raise PlanError(f"Sub-task {sub.id} has an empty description.")
        unknown = [d for d in sub.depends_on if d not in known]
        if unknown:
            raise PlanError(f"Sub-task {sub.id} depends on unknown ids: {unknown}.")
        if sub.id in sub.depends_on:
            raise PlanError(f"Sub-task {sub.id} depends on itself.")
    # Kahn's algorithm: if we can't order every node, there's a cycle.
    remaining = {s.id: set(s.depends_on) for s in sub_tasks}
    while remaining:
        ready = [i for i, deps in remaining.items() if not deps]
        if not ready:
            raise PlanError(f"Circular dependency among: {sorted(remaining)}.")
        for i in ready:
            del remaining[i]
        for deps in remaining.values():
            deps.difference_update(ready)


class PlannerAgent(Agent):
    """Generates a dependency-aware list of sub-tasks for an objective."""

    name = "planner_agent"

    @property
    def max_sub_tasks(self) -> int:
        return int(self.config.get("sub_task_count", settings.max_sub_tasks))

    def execute(self, request: AgentRequest) -> AgentResponse:
        """Generate a Plan for the objective and return it with LLM usage."""
        objective = request.prompt.strip()
        if not objective:
            return AgentResponse(
                task_id=request.task_id,
                status="error",
                error="Objective must not be empty.",
            )

        try:
            plan, usage = self.create_plan_with_usage(objective)
        except PlanError as exc:
            return AgentResponse(
                task_id=request.task_id, status="error", error=f"Planning failed: {exc}"
            )
        except Exception as exc:  # noqa: BLE001 - provider errors must not crash the pipeline
            logger.exception("Planning failed for task_id=%s", request.task_id)
            return AgentResponse(
                task_id=request.task_id,
                status="error",
                error=f"Provider error: {exc}",
            )

        return AgentResponse(
            task_id=request.task_id,
            status="success",
            result={"plan": plan.model_dump()},
            usage=usage,
        )

    def create_plan(self, objective: str) -> Plan:
        """Produce a structured Plan for the objective (usage discarded)."""
        plan, _ = self.create_plan_with_usage(objective)
        return plan

    def create_plan_with_usage(self, objective: str) -> tuple[Plan, LLMUsage]:
        """Ask the model for a plan; if the output is invalid, ask once more with
        the specific problem, then give up with PlanError."""
        prompt = (
            f"Objective: {objective}\n"
            f"Return at most {self.max_sub_tasks} sub-tasks; use fewer if the objective "
            "is simple."
        )
        usage = LLMUsage()
        last_error: PlanError | None = None
        for _attempt in range(2):
            response, call_usage = self.call_llm(prompt, system=_SYSTEM_PROMPT, kind="plan")
            usage = usage + call_usage
            try:
                return self._parse(objective, response.text), usage
            except PlanError as exc:
                last_error = exc
                logger.warning("Planner output rejected (%s); asking for a corrected plan", exc)
                prompt = (
                    f"{prompt}\n\nYour previous answer was not usable: {exc}\n"
                    "Reply again with only the corrected JSON object."
                )
        assert last_error is not None
        raise last_error

    def _parse(self, objective: str, text: str) -> Plan:
        data = extract_json_object(text)
        if data is None or not isinstance(data.get("sub_tasks"), list):
            raise PlanError('Expected a JSON object with a "sub_tasks" list.')
        try:
            sub_tasks = [SubTask.model_validate(item) for item in data["sub_tasks"]]
        except ValidationError as exc:
            raise PlanError(f"A sub-task is malformed: {exc.errors()[0]['msg']}.") from exc
        validate_plan_structure(sub_tasks, self.max_sub_tasks)
        return Plan(objective=objective, sub_tasks=sub_tasks)
