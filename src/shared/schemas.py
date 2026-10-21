"""
Data schemas used for communication across agents and orchestrator.
"""

from typing import Any

from pydantic import BaseModel


class AgentRequest(BaseModel):
    task_id: str
    prompt: str
    metadata: dict[str, Any] | None = None


class AgentResponse(BaseModel):
    task_id: str
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None
