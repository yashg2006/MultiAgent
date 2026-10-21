"""
FastAPI application entry point.

Run with: uvicorn src.api.main:app --reload
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.routes import router as tasks_router
from src.shared.db import init_db


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(
    title="Multi-Agent AI System API",
    description="HTTP interface to the Orchestrator -> Planner/Research/Validator pipeline.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    """Liveness check: the process is up and able to respond."""
    return {"status": "ok"}


app.include_router(tasks_router)
