"""
Unit tests for the exponential-backoff retry helper (src/shared/retry.py).

Satisfies docs/SRS.md NFR-03 and the "retry logic" unit test called for in
the project brief. Sleep/random are injected so these tests run instantly
and deterministically.
"""

import pytest

from src.shared.retry import RetryExhaustedError, call_with_retry


def test_call_with_retry_returns_result_on_first_success():
    calls = []

    def func():
        calls.append(1)
        return "ok"

    result = call_with_retry(func, max_retries=3, sleep_fn=lambda _: None)
    assert result == "ok"
    assert len(calls) == 1


def test_call_with_retry_retries_then_succeeds():
    attempts = {"count": 0}

    def flaky():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise ValueError("transient failure")
        return "recovered"

    result = call_with_retry(
        flaky,
        max_retries=5,
        sleep_fn=lambda _: None,
        rand_fn=lambda: 0.0,
    )
    assert result == "recovered"
    assert attempts["count"] == 3


def test_call_with_retry_raises_retry_exhausted_after_max_attempts():
    attempts = {"count": 0}

    def always_fails():
        attempts["count"] += 1
        raise ValueError("permanent failure")

    with pytest.raises(RetryExhaustedError) as exc_info:
        call_with_retry(always_fails, max_retries=3, sleep_fn=lambda _: None, rand_fn=lambda: 0.0)

    assert attempts["count"] == 3
    assert exc_info.value.attempts == 3
    assert isinstance(exc_info.value.last_error, ValueError)


def test_call_with_retry_uses_exponential_backoff():
    delays = []

    def always_fails():
        raise ValueError("fail")

    with pytest.raises(RetryExhaustedError):
        call_with_retry(
            always_fails,
            max_retries=4,
            base_delay_seconds=1.0,
            sleep_fn=delays.append,
            rand_fn=lambda: 0.0,  # jitter factor fixed at 0.5 for deterministic assertions
        )

    # delay = base * 2**(attempt-1) * 0.5, for attempts 1..3 (no sleep after the final attempt)
    assert delays == pytest.approx([0.5, 1.0, 2.0])


def test_call_with_retry_does_not_retry_on_unlisted_exception_type():
    def raises_type_error():
        raise TypeError("not retried")

    with pytest.raises(TypeError):
        call_with_retry(
            raises_type_error,
            max_retries=3,
            retry_on=(ValueError,),
            sleep_fn=lambda _: None,
        )


def test_call_with_retry_rejects_invalid_max_retries():
    with pytest.raises(ValueError):
        call_with_retry(lambda: "x", max_retries=0)
