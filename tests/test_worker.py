"""Background execution: src/worker/pipeline.py, src/worker/main.py, src/api/queue.py."""

import asyncio
import os

import pytest
from fastapi import BackgroundTasks
from sqlalchemy import select

from src.api.queue import InlineQueue, RedisQueue, make_queue
from src.orchestrator.main import Orchestrator
from src.shared.db import RunStepRecord, TaskRecord, session_scope
from src.worker.main import run_task
from src.worker.pipeline import execute_task


def add_task(task_id="t-1", text="Summarize EDF", **fields):
    with session_scope() as session:
        session.add(TaskRecord(id=task_id, input_task=text, status="pending", **fields))
    return task_id


def load(task_id):
    with session_scope() as session:
        record = session.get(TaskRecord, task_id)
        steps = session.scalars(
            select(RunStepRecord)
            .where(RunStepRecord.task_id == task_id)
            .order_by(RunStepRecord.seq)
        ).all()
        return record, steps


def test_execute_task_runs_pipeline_and_persists_steps_and_result(database_url):
    task_id = add_task()
    execute_task(task_id)
    record, steps = load(task_id)
    assert record.status == "success"
    assert set(record.result_json) == {"st-1", "st-2", "st-3"}
    assert [s.seq for s in steps] == [1, 2, 3, 4, 5]
    assert steps[1].sub_task_id == "st-1"
    assert steps[0].usage["calls"] == 1


def test_steps_are_saved_while_the_run_is_in_progress(database_url):
    task_id = add_task()
    seen_during_run = []

    class Watching(Orchestrator):
        def run(self, input_task, **kwargs):
            on_step = kwargs["on_step"]

            def watch(step):
                on_step(step)
                record, steps = load(task_id)
                seen_during_run.append((record.status, len(steps)))

            kwargs["on_step"] = watch
            return super().run(input_task, **kwargs)

    execute_task(task_id, orchestrator_factory=Watching)
    assert seen_during_run[0] == ("running", 1)
    assert seen_during_run[-1] == ("running", 5)


def test_task_cancelled_while_queued_never_starts(database_url):
    task_id = add_task(cancel_requested=True)
    execute_task(task_id, orchestrator_factory=lambda: pytest.fail("should not run"))
    record, steps = load(task_id)
    assert record.status == "cancelled"
    assert record.error == "Cancelled before it started."
    assert steps == []


def test_cancel_requested_mid_run_stops_between_stages(database_url):
    task_id = add_task()

    class CancelAfterPlanning(Orchestrator):
        def run(self, input_task, **kwargs):
            on_step = kwargs["on_step"]

            def cancel_after_first(step):
                on_step(step)
                with session_scope() as session:
                    session.get(TaskRecord, task_id).cancel_requested = True

            kwargs["on_step"] = cancel_after_first
            return super().run(input_task, **kwargs)

    execute_task(task_id, orchestrator_factory=CancelAfterPlanning)
    record, steps = load(task_id)
    assert record.status == "cancelled"
    assert [s.step_name for s in steps] == ["planner"]


def test_execute_task_is_idempotent(database_url):
    task_id = add_task()
    execute_task(task_id)
    execute_task(task_id)  # e.g. a redelivered job
    _, steps = load(task_id)
    assert len(steps) == 5


def test_unknown_task_is_ignored(database_url):
    execute_task("does-not-exist")  # must not raise


def test_crashing_pipeline_marks_task_as_error(database_url):
    task_id = add_task()

    class Exploding(Orchestrator):
        def run(self, *args, **kwargs):
            raise RuntimeError("boom")

    execute_task(task_id, orchestrator_factory=Exploding)
    record, _ = load(task_id)
    assert record.status == "error"
    assert record.error == "Internal error while running the pipeline."


def test_arq_job_function_runs_the_task(database_url):
    task_id = add_task()
    asyncio.run(run_task({}, task_id))
    assert load(task_id)[0].status == "success"


def test_inline_queue_schedules_execution_after_the_response():
    background = BackgroundTasks()
    asyncio.run(InlineQueue().enqueue("t-9", background))
    assert background.tasks[0].func is execute_task
    assert background.tasks[0].args == ("t-9",)


def test_redis_queue_enqueues_idempotent_job_and_reports_health():
    class FakePool:
        def __init__(self):
            self.jobs = []
            self.closed = False

        async def enqueue_job(self, name, *args, **kwargs):
            self.jobs.append((name, args, kwargs))

        async def ping(self):
            raise ConnectionError("down")

        async def aclose(self):
            self.closed = True

    pool = FakePool()
    queue = RedisQueue(pool)

    async def scenario():
        await queue.enqueue("t-7", BackgroundTasks())
        healthy = await queue.ping()
        await queue.close()
        return healthy

    assert asyncio.run(scenario()) is False
    assert pool.jobs == [("run_task", ("t-7",), {"_job_id": "t-7"})]
    assert pool.closed


def test_make_queue_rejects_unknown_backend():
    with pytest.raises(ValueError, match="QUEUE_BACKEND"):
        asyncio.run(make_queue("kafka", "redis://x"))


@pytest.mark.skipif(not os.getenv("REDIS_URL"), reason="needs a Redis server (CI provides one)")
def test_round_trip_through_real_redis_and_arq_worker(database_url):
    """API-side enqueue -> Redis -> arq worker (burst mode) -> task completed."""
    from arq.connections import RedisSettings
    from arq.worker import Worker

    redis_url = os.environ["REDIS_URL"]
    task_id = add_task("redis-task")

    async def scenario():
        queue = await RedisQueue.connect(redis_url)
        await queue.pool.flushdb()
        await queue.enqueue(task_id, BackgroundTasks())
        await queue.enqueue(task_id, BackgroundTasks())  # duplicate is a no-op
        worker = Worker(
            functions=[run_task],
            redis_settings=RedisSettings.from_dsn(redis_url),
            burst=True,
            poll_delay=0.05,
        )
        try:
            await worker.main()
        finally:
            await worker.close()
            await queue.close()

    asyncio.run(scenario())
    record, steps = load(task_id)
    assert record.status == "success"
    assert len(steps) == 5
