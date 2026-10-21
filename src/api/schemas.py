"""Pydantic request/response models for the API layer (distinct from the
inter-agent schemas in src/shared/schemas.py)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TaskCreateRequest(BaseModel):
    task: str = Field(..., min_length=1, description="The task string to run through the pipeline.")


class TaskOut(BaseModel):
    """API representation of a single orchestrator run."""

    id: str
    input_task: str
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None
    retries_used: int | None = None
    steps: list[dict[str, Any]] | None = None
    # Totals across all steps: calls, retries, input/output tokens, cost_usd.
    usage: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
