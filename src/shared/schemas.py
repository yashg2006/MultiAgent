"""
Data schemas used for communication across agents and orchestrator.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    task_id: str
    prompt: str
    metadata: dict[str, Any] | None = None


class LLMUsage(BaseModel):
    """Token and cost accounting for one or more LLM calls."""

    calls: int = 0
    retries: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0

    def __add__(self, other: "LLMUsage") -> "LLMUsage":
        return LLMUsage(
            calls=self.calls + other.calls,
            retries=self.retries + other.retries,
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cost_usd=round(self.cost_usd + other.cost_usd, 8),
        )


class AgentResponse(BaseModel):
    task_id: str
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None
    usage: LLMUsage | None = None


class SubTask(BaseModel):
    """A single unit of work produced by the Planner Agent."""

    id: str
    description: str
    depends_on: list[str] = Field(default_factory=list)


class Plan(BaseModel):
    """An ordered set of sub-tasks produced by the Planner Agent."""

    objective: str
    sub_tasks: list[SubTask] = Field(default_factory=list)


class ValidationStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"


class ValidationResult(BaseModel):
    """Structured output of the Validator Agent."""

    status: ValidationStatus
    score: float | None = None
    reasons: list[str] = Field(default_factory=list)


class RunStep(BaseModel):
    """A single traced step in an orchestrator run, for logging/debugging."""

    step_name: str
    status: str
    latency_seconds: float
    detail: dict[str, Any] | None = None
    sub_task_id: str | None = None
    usage: LLMUsage = Field(default_factory=LLMUsage)


class RunResult(BaseModel):
    """Final output of an Orchestrator.run() call.

    `status` is one of "success", "partial", "error", or "cancelled".
    """

    task_id: str
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None
    steps: list[RunStep] = Field(default_factory=list)
    retries_used: int = 0
    usage: LLMUsage = Field(default_factory=LLMUsage)
