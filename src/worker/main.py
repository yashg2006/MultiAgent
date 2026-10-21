"""
Redis queue worker (arq).

Run with:  arq src.worker.main.WorkerSettings

The API enqueues `run_task` jobs (job id = task id, so a task can't be queued
twice); each worker process runs up to WORKER_MAX_JOBS of them concurrently.
Pipelines are synchronous, so each runs in a thread.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from arq.connections import RedisSettings

from src.shared.config import settings
from src.shared.db import configure_database
from src.worker.pipeline import execute_task


async def run_task(ctx: dict[str, Any], task_id: str) -> None:
    await asyncio.to_thread(execute_task, task_id)


async def startup(ctx: dict[str, Any]) -> None:
    configure_database()


class WorkerSettings:
    functions = [run_task]
    on_startup = startup
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = int(os.getenv("WORKER_MAX_JOBS", "4"))
    # Upper bound for one run; a stuck provider call is cut off well before
    # this by LLM_TIMEOUT_SECONDS and the circuit breaker.
    job_timeout = int(os.getenv("WORKER_JOB_TIMEOUT_SECONDS", "900"))
    # Don't let arq re-run a failed pipeline on its own: execute_task already
    # records failures on the task, and a blind retry would bill the LLM again.
    max_tries = 1
