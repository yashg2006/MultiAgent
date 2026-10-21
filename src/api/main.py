"""
FastAPI application entry point.

Run with: uvicorn src.api.main:app --reload
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from src.api.queue import make_queue
from src.api.routes import router as tasks_router
from src.shared.config import settings
from src.shared.db import configure_database, get_engine, run_migrations
from src.shared.utils import setup_logger

logger = setup_logger(__name__)

# Comma-separated list of browser origins allowed to call the API. Defaults to
# the Vite dev server; set CORS_ORIGINS for any deployed frontend.
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

# Apply migrations on startup (convenient for one dev process). Docker Compose
# sets this to false and runs migrations once in a separate step instead, so
# several API replicas don't race to migrate.
AUTO_MIGRATE = os.getenv("AUTO_MIGRATE", "true").lower() == "true"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_database()
    if AUTO_MIGRATE:
        await run_in_threadpool(run_migrations)
    app.state.queue = await make_queue(settings.queue_backend, settings.redis_url)
    logger.info("API ready (queue=%s)", app.state.queue.name)
    yield
    await app.state.queue.close()


app = FastAPI(
    title="Multi-Agent AI System API",
    description="HTTP interface to the Orchestrator -> Planner/Research/Validator pipeline.",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Last-Event-ID"],
)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    """Liveness: the process is up and able to respond."""
    return {"status": "ok"}


@app.get("/ready", tags=["meta"])
async def ready() -> JSONResponse:
    """Readiness: the database and the task queue are reachable."""

    def database_ok() -> bool:
        try:
            with get_engine().connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except Exception:  # noqa: BLE001 - readiness reports, never raises
            logger.exception("Readiness: database check failed")
            return False

    checks = {
        "database": "ok" if await run_in_threadpool(database_ok) else "unavailable",
        "queue": "ok" if await app.state.queue.ping() else "unavailable",
    }
    healthy = all(value == "ok" for value in checks.values())
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={"status": "ready" if healthy else "not ready", **checks},
    )


app.include_router(tasks_router)
