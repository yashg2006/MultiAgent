"""
Planner Agent implementation.
Responsible for breaking down high-level objectives into executable sub-tasks.
"""

from __future__ import annotations

from src.agents.base import Agent
from src.shared.schemas import AgentRequest, AgentResponse, Plan, SubTask
from src.shared.utils import setup_logger

logger = setup_logger(__name__)

_PLAN_SYSTEM_PROMPT = (
    "You are a planning assistant. Given a high-level objective, break it down "
    "into 2-5 concrete, independently-researchable sub-tasks. Respond with a "
    "short description per sub-task."
)


class PlannerAgent(Agent):
    """Generates a list of sub-tasks for a given objective."""

    name = "planner_agent"

    def execute(self, request: AgentRequest) -> AgentResponse:
        """Generate a Plan (ordered sub-tasks) for the given objective and return it."""
        objective = request.prompt.strip()
        if not objective:
            return AgentResponse(
                task_id=request.task_id,
                status="error",
                error="Objective must not be empty.",
            )

        try:
            plan = self.create_plan(objective)
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
        )

    def create_plan(self, objective: str) -> Plan:
        """
        Produce a structured Plan for the given objective.

        With the Mock provider this deterministically derives 3 sub-tasks
        from the objective text, so pipeline tests don't depend on real LLM
        output while still exercising the full data flow.
        """
        raw = self.provider.complete(objective, system=_PLAN_SYSTEM_PROMPT)
        sub_task_count = self.config.get("sub_task_count", 3)
        sub_tasks = [
            SubTask(
                id=f"st-{i + 1}",
                description=f"Research aspect {i + 1} of: {objective} (ref: {raw[:40]})",
            )
            for i in range(sub_task_count)
        ]
        return Plan(objective=objective, sub_tasks=sub_tasks)
