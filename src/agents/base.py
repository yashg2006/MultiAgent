"""
Base contract for all agents.

Satisfies NFR-02 ("the architecture shall support addition of new agent
types without modifying the orchestrator core logic") and FR-05 ("the
system shall pass structured data between agents using shared Pydantic
schemas"): a new agent subclasses `Agent`, implements `execute()`, and is
registered with the Orchestrator — no orchestrator code changes required.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.shared.llm_provider import (
    LLMProvider,
    LLMResult,
    generate_with_resilience,
    provider_from_settings,
)
from src.shared.schemas import AgentRequest, AgentResponse, LLMUsage


class Agent(ABC):
    """Common interface every agent (Research, Planner, Validator, ...) implements."""

    name: str = "agent"

    def __init__(self, provider: LLMProvider | None = None, config: dict | None = None) -> None:
        """
        Args:
            provider: an LLMProvider to use; defaults to the one configured via
                the LLM_PROVIDER environment variable (see src/shared/config.py),
                which is "mock" unless overridden — so `SomeAgent()` works
                standalone in tests and demos with no API key required.
            config: optional agent-specific configuration.
        """
        self.provider = provider or provider_from_settings()
        self.config = config or {}

    def call_llm(
        self, prompt: str, *, system: str | None = None, kind: str = "text"
    ) -> tuple[LLMResult, LLMUsage]:
        """The one way agents call a model: retries, circuit breaker, and usage
        accounting included. Thread-safe; agents keep no per-call state."""
        return generate_with_resilience(self.provider, prompt, system=system, kind=kind)

    @abstractmethod
    def execute(self, request: AgentRequest) -> AgentResponse:
        """
        Process a single AgentRequest and return a structured AgentResponse.

        Implementations should never raise for expected failure modes (bad
        input, provider error); they should catch and return an
        AgentResponse with status="error" and `error` set, so the
        Orchestrator's retry/aggregation logic has a single uniform contract
        to handle.
        """
        raise NotImplementedError
