"""
Research Agent implementation.
Responsible for fetching context, web searching, and data retrieval.
"""

from __future__ import annotations

from src.agents.base import Agent
from src.shared.schemas import AgentRequest, AgentResponse
from src.shared.utils import setup_logger

logger = setup_logger(__name__)


class ResearchAgent(Agent):
    """
    Gathers information relevant to a sub-task.

    The current implementation delegates to the configured LLM provider to
    synthesize a research summary for the given query. A real "pluggable
    search/retrieval tool" (per the project brief) can later be substituted
    behind the same `execute()` contract without touching the Orchestrator.
    """

    name = "research_agent"

    def execute(self, request: AgentRequest) -> AgentResponse:
        """Execute a research query and return structured results."""
        query = request.prompt.strip()
        if not query:
            return AgentResponse(
                task_id=request.task_id,
                status="error",
                error="Research query must not be empty.",
            )

        try:
            findings = self.provider.complete(
                query,
                system=(
                    "You are a research assistant. Given a query, return a concise, "
                    "factual summary of relevant findings."
                ),
            )
        except Exception as exc:  # noqa: BLE001 - provider errors must not crash the pipeline
            logger.exception("Research provider call failed for task_id=%s", request.task_id)
            return AgentResponse(
                task_id=request.task_id,
                status="error",
                error=f"Provider error: {exc}",
            )

        return AgentResponse(
            task_id=request.task_id,
            status="success",
            result={"query": query, "findings": findings},
        )
