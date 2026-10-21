"""
Research Agent implementation.
Responsible for fetching context, web searching, and data retrieval.
"""

from __future__ import annotations

from src.agents.base import Agent
from src.shared.config import settings
from src.shared.llm_provider import LLMProvider
from src.shared.schemas import AgentRequest, AgentResponse
from src.shared.search import SearchTool, get_search_tool
from src.shared.utils import setup_logger

logger = setup_logger(__name__)

_SYSTEM_PROMPT = (
    "You are a research assistant working on one part of a larger task. Answer the "
    "question concisely and factually in under 200 words. If search results are "
    "provided, use them where relevant and name the sources you relied on. If you are "
    "unsure of something, say so rather than guessing."
)


class ResearchAgent(Agent):
    """
    Answers one sub-task, optionally grounded in search results and in the
    findings of sub-tasks it depends on (passed by the Orchestrator as
    `request.metadata["context"]`).
    """

    name = "research_agent"

    def __init__(
        self,
        provider: LLMProvider | None = None,
        config: dict | None = None,
        search_tool: SearchTool | None = None,
    ) -> None:
        super().__init__(provider, config)
        self.search_tool = search_tool or get_search_tool(settings.search_tool)

    def build_prompt(
        self,
        query: str,
        context: dict[str, str],
        hits: list,
        feedback: list[str] | None = None,
    ) -> str:
        """Assemble the model prompt from the question, dependencies, sources,
        and (on a retry) the validator's feedback on the previous attempt."""
        parts = [f"Question: {query}"]
        if context:
            parts.append("Findings from earlier steps you can build on:")
            parts.extend(f"- [{sub_id}] {text}" for sub_id, text in context.items())
        if hits:
            parts.append("Search results:")
            parts.extend(f"- {hit.title}: {hit.snippet} ({hit.url})" for hit in hits)
        if feedback:
            parts.append("A reviewer rejected the previous answers. Address this feedback:")
            parts.extend(f"- {item}" for item in feedback)
        return "\n".join(parts)

    def execute(self, request: AgentRequest) -> AgentResponse:
        """Execute a research query and return structured results."""
        query = request.prompt.strip()
        if not query:
            return AgentResponse(
                task_id=request.task_id,
                status="error",
                error="Research query must not be empty.",
            )

        metadata = request.metadata or {}
        context = metadata.get("context") or {}
        feedback = metadata.get("feedback") or []
        hits = self.search_tool.search(query)
        prompt = (
            self.build_prompt(query, context, hits, feedback)
            if (context or hits or feedback)
            else query
        )

        try:
            response, usage = self.call_llm(prompt, system=_SYSTEM_PROMPT)
        except Exception as exc:  # noqa: BLE001 - provider errors must not crash the pipeline
            logger.exception("Research provider call failed for task_id=%s", request.task_id)
            return AgentResponse(
                task_id=request.task_id,
                status="error",
                error=f"Provider error: {exc}",
            )

        result: dict = {"query": query, "findings": response.text}
        if hits:
            result["sources"] = [{"title": h.title, "url": h.url} for h in hits]
        return AgentResponse(task_id=request.task_id, status="success", result=result, usage=usage)
