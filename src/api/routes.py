"""
API routes for submitting, watching, and cancelling pipeline runs.

POST /tasks              start a run (returns immediately, status "pending")
GET  /tasks              recent runs, newest first (without step detail)
GET  /tasks/{id}         one run, including its steps so far
GET  /tasks/{id}/events  live step stream (Server-Sent Events)
POST /tasks/{id}/cancel  ask a queued or running run to stop
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from src.api.auth import UserOut, current_user
from src.api.rate_limit import enforce_rate_limit
from src.api.schemas import TaskCreateRequest, TaskOut
from src.shared.config import settings
from src.shared.db import TERMINAL_STATUSES, RunStepRecord, TaskRecord, session_scope
from src.shared.schemas import LLMUsage
from src.shared.utils import setup_logger

logger = setup_logger(__name__)
# Every route requires a signed-in user and only ever sees that user's runs;
# someone else's task id behaves exactly like a nonexistent one (404).
router = APIRouter(prefix="/tasks", tags=["tasks"])


def _usage_total(steps: list[dict]) -> dict | None:
    if not steps:
        return None
    total = LLMUsage()
    for step in steps:
        if isinstance(step.get("usage"), dict):
            total = total + LLMUsage.model_validate(step["usage"])
    return total.model_dump()


def _to_task_out(record: TaskRecord, steps: list[dict] | None) -> TaskOut:
    return TaskOut(
        id=record.id,
        input_task=record.input_task,
        status=record.status,
        result=record.result_json,
        error=record.error,
        retries_used=record.retries_used,
        cancel_requested=record.cancel_requested,
        steps=steps,
        usage=_usage_total(steps or []),
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _owned(session, task_id: str, user_id: str) -> TaskRecord | None:
    record = session.get(TaskRecord, task_id)
    return record if record is not None and record.user_id == user_id else None


def _load_task(
    task_id: str, user_id: str, *, after_seq: int = 0
) -> tuple[TaskOut, list[dict]] | None:
    """The user's task plus its steps with seq > after_seq (all steps if 0)."""
    with session_scope() as session:
        record = _owned(session, task_id, user_id)
        if record is None:
            return None
        rows = session.scalars(
            select(RunStepRecord)
            .where(RunStepRecord.task_id == task_id, RunStepRecord.seq > after_seq)
            .order_by(RunStepRecord.seq)
        ).all()
        new_steps = [row.to_dict() for row in rows]
        if after_seq == 0:
            return _to_task_out(record, new_steps), new_steps
        return _to_task_out(record, None), new_steps


def _get_or_404(task_id: str, user_id: str) -> TaskOut:
    loaded = _load_task(task_id, user_id)
    if loaded is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id!r} not found.")
    return loaded[0]


@router.post("", response_model=TaskOut, status_code=201)
async def create_task(
    payload: TaskCreateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    user: UserOut = Depends(current_user),
) -> TaskOut:
    """Start a run. Follow it with GET /tasks/{id}/events or poll GET /tasks/{id}."""
    await enforce_rate_limit(request, f"tasks:{user.id}", settings.task_rate_limit_per_minute)
    task_id = str(uuid.uuid4())

    def insert() -> TaskOut:
        with session_scope() as session:
            record = TaskRecord(
                id=task_id, user_id=user.id, input_task=payload.task, status="pending"
            )
            session.add(record)
            session.flush()
            return _to_task_out(record, [])

    task_out = await run_in_threadpool(insert)
    await request.app.state.queue.enqueue(task_id, background_tasks)
    return task_out


@router.get("", response_model=list[TaskOut])
def list_tasks(limit: int = 50, user: UserOut = Depends(current_user)) -> list[TaskOut]:
    """Your recent runs, newest first. Steps are omitted; fetch a run for them."""
    with session_scope() as session:
        records = session.scalars(
            select(TaskRecord)
            .where(TaskRecord.user_id == user.id)
            .order_by(TaskRecord.created_at.desc())
            .limit(max(1, min(limit, 200)))
        ).all()
        return [_to_task_out(r, None) for r in records]


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: str, user: UserOut = Depends(current_user)) -> TaskOut:
    """A run's current status, result, and steps so far."""
    return _get_or_404(task_id, user.id)


@router.post("/{task_id}/cancel", response_model=TaskOut, status_code=202)
def cancel_task(task_id: str, user: UserOut = Depends(current_user)) -> TaskOut:
    """Ask a run to stop. It stops between stages, keeping finished work."""
    with session_scope() as session:
        record = _owned(session, task_id, user.id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"Task {task_id!r} not found.")
        if record.status in TERMINAL_STATUSES:
            raise HTTPException(
                status_code=409, detail=f"Task already finished with status {record.status!r}."
            )
        record.cancel_requested = True
    return _get_or_404(task_id, user.id)


def _sse(event: str, data: object, event_id: int | None = None) -> str:
    lines = []
    if event_id is not None:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event}")
    lines.append(f"data: {json.dumps(data, default=str)}")
    return "\n".join(lines) + "\n\n"


@router.get("/{task_id}/events")
async def task_events(
    task_id: str, request: Request, user: UserOut = Depends(current_user)
) -> StreamingResponse:
    """
    Server-Sent Events for one run:
      event: step    one finished step (event id = its seq)
      event: status  the run's status changed
      event: done    final task (same shape as GET /tasks/{id}); stream ends
    Reconnecting clients send Last-Event-ID and resume after that step.
    """
    if await run_in_threadpool(_load_task, task_id, user.id, after_seq=10**9) is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id!r} not found.")
    try:
        last_seq = int(request.headers.get("last-event-id") or 0)
    except ValueError:
        last_seq = 0

    async def stream() -> AsyncIterator[str]:
        nonlocal last_seq
        last_status: str | None = None
        since_keepalive = 0.0
        yield "retry: 2000\n\n"
        while True:
            if await request.is_disconnected():
                return
            loaded = await run_in_threadpool(_load_task, task_id, user.id, after_seq=last_seq)
            if loaded is None:
                return
            task, new_steps = loaded
            for step in new_steps:
                last_seq = step["seq"]
                yield _sse("step", step, event_id=step["seq"])
            if task.status != last_status:
                last_status = task.status
                yield _sse(
                    "status", {"status": task.status, "cancel_requested": task.cancel_requested}
                )
            if task.status in TERMINAL_STATUSES:
                final = await run_in_threadpool(_get_or_404, task_id, user.id)
                yield _sse("done", final.model_dump(mode="json"))
                return
            await asyncio.sleep(settings.sse_poll_seconds)
            since_keepalive += settings.sse_poll_seconds
            if since_keepalive >= settings.sse_keepalive_seconds:
                since_keepalive = 0.0
                yield ": keep-alive\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
