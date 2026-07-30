"""
Data schemas used for communication across agents and orchestrator.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel

class AgentRequest(BaseModel):
    task_id: str
    prompt: str
    metadata: Optional[Dict[str, Any]] = None

class AgentResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
