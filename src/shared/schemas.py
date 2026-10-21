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


class AgentResponse(BaseModel):
    task_id: str
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None


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


class RunResult(BaseModel):
    """Final output of an Orchestrator.run() call."""

    task_id: str
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None
    steps: list[RunStep] = Field(default_factory=list)
    retries_used: int = 0
