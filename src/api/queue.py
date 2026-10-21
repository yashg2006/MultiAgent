"""
How the API hands a new task to something that runs it.

- `InlineQueue` (QUEUE_BACKEND=inline): runs the task in this API process
  after the response is sent. No Redis needed; for development and tests.
- `RedisQueue` (QUEUE_BACKEND=redis): enqueues an arq job; separate worker
  processes run it. The API stays stateless, so API and workers scale
  independently.
"""

from __future__ import annotations

from typing import Any, Protocol

from fastapi import BackgroundTasks

from src.worker.pipeline import execute_task


class TaskQueue(Protocol):
    name: str

    async def enqueue(self, task_id: str, background: BackgroundTasks) -> None: ...

    async def ping(self) -> bool: ...

    async def close(self) -> None: ...


class InlineQueue:
    name = "inline"

    async def enqueue(self, task_id: str, background: BackgroundTasks) -> None:
        background.add_task(execute_task, task_id)

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        return None


class RedisQueue:
    name = "redis"

    def __init__(self, pool: Any) -> None:
        self.pool = pool

    @classmethod
    async def connect(cls, redis_url: str) -> RedisQueue:
        from arq import create_pool
        from arq.connections import RedisSettings

        return cls(await create_pool(RedisSettings.from_dsn(redis_url)))

    async def enqueue(self, task_id: str, background: BackgroundTasks) -> None:
        # Using the task id as the job id makes enqueueing idempotent.
        await self.pool.enqueue_job("run_task", task_id, _job_id=task_id)

    async def ping(self) -> bool:
        try:
            return bool(await self.pool.ping())
        except Exception:  # noqa: BLE001 - readiness reports, never raises
            return False

    async def close(self) -> None:
        closer = getattr(self.pool, "aclose", None) or self.pool.close
        await closer()


async def make_queue(backend: str, redis_url: str) -> TaskQueue:
    normalized = backend.strip().lower()
    if normalized == "inline":
        return InlineQueue()
    if normalized == "redis":
        return await RedisQueue.connect(redis_url)
    raise ValueError(f"Unknown QUEUE_BACKEND: {backend!r} (expected 'inline' or 'redis')")
