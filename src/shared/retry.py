"""
Retry helper implementing exponential backoff with jitter.

Satisfies NFR-03 in docs/SRS.md: "The system shall implement retry logic
(max 3 attempts) with exponential backoff for transient API failures."
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from typing import TypeVar

from src.shared.utils import setup_logger

T = TypeVar("T")

logger = setup_logger(__name__)


class RetryExhaustedError(Exception):
    """Raised when all retry attempts have been exhausted."""

    def __init__(self, attempts: int, last_error: Exception) -> None:
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(f"Retry exhausted after {attempts} attempt(s): {last_error}")


def call_with_retry(
    func: Callable[[], T],
    *,
    max_retries: int = 3,
    base_delay_seconds: float = 0.5,
    max_delay_seconds: float = 10.0,
    retry_on: tuple[type[Exception], ...] = (Exception,),
    sleep_fn: Callable[[float], None] = time.sleep,
    rand_fn: Callable[[], float] = random.random,
    on_retry: Callable[[int, Exception], None] | None = None,
) -> T:
    """
    Call `func` and retry on failure with exponential backoff + jitter.

    Args:
        func: zero-argument callable to invoke.
        max_retries: maximum number of attempts (including the first).
        base_delay_seconds: base delay for the backoff calculation.
        max_delay_seconds: cap on the computed delay before jitter.
        retry_on: exception types that should trigger a retry; anything else
            propagates immediately.
        sleep_fn / rand_fn: injectable for deterministic unit testing.
        on_retry: called with (attempt_number, error) before each retry, e.g.
            to count retries for metrics.

    Returns:
        The return value of `func` on success.

    Raises:
        RetryExhaustedError: if all attempts fail.
    """
    if max_retries < 1:
        raise ValueError("max_retries must be >= 1")

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            return func()
        except retry_on as exc:  # noqa: PERF203 - clarity over micro-optimisation here
            last_error = exc
            if attempt == max_retries:
                break
            delay = min(base_delay_seconds * (2 ** (attempt - 1)), max_delay_seconds)
            jittered_delay = delay * (0.5 + rand_fn())
            logger.warning(
                "Attempt %d/%d failed (%s); retrying in %.2fs",
                attempt,
                max_retries,
                exc,
                jittered_delay,
            )
            if on_retry is not None:
                on_retry(attempt, exc)
            sleep_fn(jittered_delay)

    assert last_error is not None  # noqa: S101 - unreachable otherwise, guards type-checkers
    raise RetryExhaustedError(attempts=max_retries, last_error=last_error)
