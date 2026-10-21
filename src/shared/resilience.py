"""
Circuit breaker for calls to external services (LLM providers).

After `failure_threshold` consecutive failures the breaker "opens" and calls
fail immediately with `CircuitOpenError` for `reset_seconds`. After that, one
trial call is allowed ("half-open"): success closes the breaker, failure opens
it again. This stops a pipeline from waiting through full retry/backoff cycles
on every call while a provider is down.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


class CircuitOpenError(RuntimeError):
    """Raised instead of calling a service whose circuit is open."""


class CircuitBreaker:
    """Thread-safe consecutive-failure circuit breaker."""

    def __init__(
        self,
        failure_threshold: int = 5,
        reset_seconds: float = 30.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        self.failure_threshold = failure_threshold
        self.reset_seconds = reset_seconds
        self._clock = clock
        self._lock = threading.Lock()
        self._failures = 0
        self._opened_at: float | None = None

    @property
    def state(self) -> str:
        """'closed', 'open', or 'half_open'."""
        with self._lock:
            return self._state_unlocked()

    def _state_unlocked(self) -> str:
        if self._opened_at is None:
            return "closed"
        if self._clock() - self._opened_at >= self.reset_seconds:
            return "half_open"
        return "open"

    def call(self, func: Callable[[], T]) -> T:
        """Run `func` through the breaker."""
        with self._lock:
            if self._state_unlocked() == "open":
                raise CircuitOpenError(
                    f"Circuit open after {self._failures} consecutive failures; "
                    f"retrying after {self.reset_seconds:.0f}s."
                )
        try:
            result = func()
        except Exception:
            with self._lock:
                self._failures += 1
                if self._failures >= self.failure_threshold or self._opened_at is not None:
                    # Reaching the threshold opens it; a failed half-open trial
                    # re-opens it with a fresh cooldown.
                    self._opened_at = self._clock()
            raise
        with self._lock:
            self._failures = 0
            self._opened_at = None
        return result
