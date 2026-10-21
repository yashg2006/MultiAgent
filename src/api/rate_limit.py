"""
Fixed-window rate limiting.

Counts requests per key per minute. With QUEUE_BACKEND=redis the counts live
in Redis (shared by every API instance); otherwise in this process's memory,
which is enough for a single development server.
"""

from __future__ import annotations

import threading
import time
from typing import Any

from fastapi import HTTPException, Request

from src.shared.config import settings

WINDOW_SECONDS = 60


class InMemoryRateLimiter:
    def __init__(self, clock=time.time) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._counts: dict[tuple[str, int], int] = {}

    async def hit(self, key: str) -> tuple[int, int]:
        """Count one request; return (count in this window, seconds until reset)."""
        now = self._clock()
        window = int(now // WINDOW_SECONDS)
        with self._lock:
            # Drop old windows so memory stays bounded.
            for stale in [k for k in self._counts if k[1] < window]:
                del self._counts[stale]
            count = self._counts.get((key, window), 0) + 1
            self._counts[(key, window)] = count
        return count, int(WINDOW_SECONDS - now % WINDOW_SECONDS) + 1


class RedisRateLimiter:
    def __init__(self, redis: Any, clock=time.time) -> None:
        self._redis = redis
        self._clock = clock

    async def hit(self, key: str) -> tuple[int, int]:
        now = self._clock()
        window = int(now // WINDOW_SECONDS)
        redis_key = f"ratelimit:{key}:{window}"
        count = int(await self._redis.incr(redis_key))
        if count == 1:
            await self._redis.expire(redis_key, WINDOW_SECONDS * 2)
        return count, int(WINDOW_SECONDS - now % WINDOW_SECONDS) + 1


def client_ip(request: Request) -> str:
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def enforce_rate_limit(request: Request, key: str, limit: int) -> None:
    """Raise HTTP 429 (with Retry-After) once `key` exceeds `limit` per minute."""
    if limit <= 0:
        return
    limiter = request.app.state.rate_limiter
    count, retry_after = await limiter.hit(key)
    if count > limit:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Try again in a minute.",
            headers={"Retry-After": str(retry_after)},
        )
