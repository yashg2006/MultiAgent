"""
Run one queued task end to end and persist everything about it.

Used by both execution modes: in-process (`QUEUE_BACKEND=inline`, via FastAPI
background tasks) and the Redis worker (`src/worker/main.py`). It is safe to
call twice for the same task (e.g. a redelivered job): only a task still in
`pending` is started.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from sqlalchemy import select

from src.orchestrator.main import Orchestrator
from src.shared.config import settings
from src.shared.observability import record_run, record_step, request_id_var, task_id_var
from src.shared.db import RunStepRecord, TaskRecord, serialize, session_scope
from src.shared.schemas import RunStep
from src.shared.utils import setup_logger

logger = setup_logger(__name__)


def _claim(task_id: str) -> str | None:
    """Move a pending task to running and return its input; None if there's
    nothing to run (unknown, already started, or cancelled while queued)."""
    with session_scope() as session:
        record = session.get(TaskRecord, task_id, with_for_update=True)
        if record is None:
            logger.error("Task %s not found; nothing to run", task_id)
            return None
        if record.status != "pending":
            logger.info("Task %s is %s, not pending; skipping", task_id, record.status)
            return None
        if record.cancel_requested:
            record.status = "cancelled"
            record.error = "Cancelled before it started."
            return None
        record.status = "running"
        return record.input_task


def execute_task(
    task_id: str,
    orchestrator_factory: Callable[[], Orchestrator] = Orchestrator,
    request_id: str | None = None,
) -> None:
    """Run the pipeline for `task_id`, saving each step as it finishes.

    `request_id` (from the API request that created the task) is attached to
    every log line of the run, so API and worker logs can be joined.
    """
    task_token = task_id_var.set(task_id)
    request_token = request_id_var.set(request_id) if request_id else None
    try:
        _execute(task_id, orchestrator_factory)
    finally:
        task_id_var.reset(task_token)
        if request_token is not None:
            request_id_var.reset(request_token)


def _execute(task_id: str, orchestrator_factory: Callable[[], Orchestrator]) -> None:
    input_task = _claim(task_id)
    if input_task is None:
        return

    logger.info("Run started")
    started = time.monotonic()
    provider = settings.llm_provider
    seq = 0

    def save_step(step: RunStep) -> None:
        nonlocal seq
        seq += 1
        record_step(step, provider)
        with session_scope() as session:
            session.add(
                RunStepRecord(
                    task_id=task_id,
                    seq=seq,
                    step_name=step.step_name,
                    status=step.status,
                    latency_seconds=step.latency_seconds,
                    sub_task_id=step.sub_task_id,
                    detail=serialize(step.detail),
                    usage=step.usage.model_dump(),
                )
            )

    def cancel_requested() -> bool:
        with session_scope() as session:
            return bool(
                session.scalar(select(TaskRecord.cancel_requested).where(TaskRecord.id == task_id))
            )

    try:
        result = orchestrator_factory().run(
            input_task, task_id=task_id, on_step=save_step, should_cancel=cancel_requested
        )
    except Exception:  # noqa: BLE001 - a crash must still leave a readable task
        logger.exception("Pipeline crashed for task_id=%s", task_id)
        with session_scope() as session:
            record = session.get(TaskRecord, task_id)
            if record is not None:
                record.status = "error"
                record.error = "Internal error while running the pipeline."
        return

    with session_scope() as session:
        record = session.get(TaskRecord, task_id)
        if record is None:
            logger.error("Task %s disappeared while running", task_id)
            return
        record.status = result.status
        record.result_json = serialize(result.result)
        record.error = result.error
        record.retries_used = result.retries_used
    duration = time.monotonic() - started
    record_run(result, duration)
    logger.info(
        "Run finished",
        extra={
            "status": result.status,
            "duration_seconds": round(duration, 3),
            "llm_calls": result.usage.calls,
            "cost_usd": result.usage.cost_usd,
        },
    )
