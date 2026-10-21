"""Pydantic request/response models for the API layer (distinct from the
inter-agent schemas in src/shared/schemas.py)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

MAX_TASK_LENGTH = 2000


class TaskCreateRequest(BaseModel):
    task: str = Field(
        ...,
        min_length=1,
        max_length=MAX_TASK_LENGTH,
        description="The goal to run through the pipeline.",
    )

    @field_validator("task")
    @classmethod
    def strip_and_require_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Task must contain some text.")
        return value


class TaskOut(BaseModel):
    """API representation of a single orchestrator run.

    status: pending (queued), running, success, partial, error, or cancelled.
    """

    id: str
    input_task: str
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None
    retries_used: int | None = None
    cancel_requested: bool = False
    # Steps in the order they finished; omitted (null) in list responses.
    steps: list[dict[str, Any]] | None = None
    # Totals across all steps: calls, retries, input/output tokens, cost_usd.
    usage: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
