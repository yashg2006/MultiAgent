"""
API routes for submitting and inspecting multi-agent pipeline runs.

POST /tasks   - submit a task; runs in the background, returns immediately
                with status="pending"
GET  /tasks   - list all tasks (most recent first)
GET  /tasks/{id} - fetch a single task's current status/result
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session

from src.api.schemas import TaskCreateRequest, TaskOut
from src.orchestrator.main import Orchestrator
from src.shared.db import TaskRecord, get_session, serialize_steps
from src.shared.schemas import LLMUsage
from src.shared.utils import setup_logger

logger = setup_logger(__name__)
router = APIRouter(prefix="/tasks", tags=["tasks"])


def _usage_from_steps(steps: list[dict] | None) -> dict | None:
    if not steps:
        return None
    total = LLMUsage()
    for step in steps:
        if isinstance(step.get("usage"), dict):
            total = total + LLMUsage.model_validate(step["usage"])
    return total.model_dump()


def _to_task_out(record: TaskRecord) -> TaskOut:
    return TaskOut(
        usage=_usage_from_steps(record.steps_json),
        id=record.id,
        input_task=record.input_task,
        status=record.status,
        result=record.result_json,
        error=record.error,
        retries_used=record.retries_used,
        steps=record.steps_json,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _run_task_in_background(task_id: str, input_task: str) -> None:
    """
    Execute the orchestrator pipeline and persist the outcome.

    Runs via FastAPI's BackgroundTasks, which executes sync callables in a
    threadpool so it never blocks the event loop. Opens its own DB session
    since the request-scoped one is already closed by the time this runs.
    """
    session: Session = get_session()
    try:
        orchestrator = Orchestrator()
        result = orchestrator.run(input_task, task_id=task_id)

        record = session.get(TaskRecord, task_id)
        if record is None:
            logger.error("Task record %s disappeared before background run completed", task_id)
            return

        record.status = result.status
        record.result_json = result.result
        record.error = result.error
        record.retries_used = result.retries_used
        record.steps_json = serialize_steps(result.steps)
        session.commit()
    except Exception:  # noqa: BLE001 - a crash here must still leave a readable task record
        logger.exception("Background orchestrator run failed for task_id=%s", task_id)
        record = session.get(TaskRecord, task_id)
        if record is not None:
            record.status = "error"
            record.error = "Internal error while running the pipeline."
            session.commit()
    finally:
        session.close()


@router.post("", response_model=TaskOut, status_code=201)
def create_task(request: TaskCreateRequest, background_tasks: BackgroundTasks) -> TaskOut:
    """Submit a new task. The pipeline runs asynchronously; poll GET /tasks/{id} for the result."""
    task_id = str(uuid.uuid4())
    session = get_session()
    try:
        record = TaskRecord(id=task_id, input_task=request.task, status="pending")
        session.add(record)
        session.commit()
        session.refresh(record)
        task_out = _to_task_out(record)
    finally:
        session.close()

    background_tasks.add_task(_run_task_in_background, task_id, request.task)
    return task_out


@router.get("", response_model=list[TaskOut])
def list_tasks(limit: int = 50) -> list[TaskOut]:
    """List tasks, most recently created first."""
    session = get_session()
    try:
        records = (
            session.query(TaskRecord).order_by(TaskRecord.created_at.desc()).limit(limit).all()
        )
        return [_to_task_out(r) for r in records]
    finally:
        session.close()


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: str) -> TaskOut:
    """Fetch a single task's current status and result."""
    session = get_session()
    try:
        record = session.get(TaskRecord, task_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"Task {task_id!r} not found.")
        return _to_task_out(record)
    finally:
        session.close()
