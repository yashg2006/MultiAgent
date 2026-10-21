"""
FastAPI application entry point.

Run with: uvicorn src.api.main:app --reload
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router as tasks_router
from src.shared.db import init_db

# Comma-separated list of browser origins allowed to call the API. Defaults to
# the Vite dev server; set CORS_ORIGINS for any deployed frontend.
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    """Liveness check: the process is up and able to respond."""
    return {"status": "ok"}


app.include_router(tasks_router)
