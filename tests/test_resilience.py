"""Circuit breaker (src/shared/resilience.py) and resilient LLM calls."""

import pytest

from src.shared.config import settings
from src.shared.llm_provider import generate_with_resilience
from src.shared.resilience import CircuitBreaker, CircuitOpenError
from src.shared.retry import RetryExhaustedError
from tests.fakes import ScriptedProvider, TransientError


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def _fail():
    raise ValueError("down")


def test_breaker_opens_after_threshold_and_fails_fast():
    clock = FakeClock()
    breaker = CircuitBreaker(failure_threshold=2, reset_seconds=10, clock=clock)
    for _ in range(2):
        with pytest.raises(ValueError):
            breaker.call(_fail)
    assert breaker.state == "open"
    calls = []
    with pytest.raises(CircuitOpenError):
        breaker.call(lambda: calls.append(1))
    assert calls == []  # the function was never invoked


def test_breaker_half_open_trial_success_closes_it():
    clock = FakeClock()
    breaker = CircuitBreaker(failure_threshold=1, reset_seconds=10, clock=clock)
    with pytest.raises(ValueError):
        breaker.call(_fail)
    clock.now = 10.0
    assert breaker.state == "half_open"
    assert breaker.call(lambda: "ok") == "ok"
    assert breaker.state == "closed"


def test_breaker_half_open_trial_failure_reopens_with_fresh_cooldown():
    clock = FakeClock()
    breaker = CircuitBreaker(failure_threshold=1, reset_seconds=10, clock=clock)
    with pytest.raises(ValueError):
        breaker.call(_fail)
    clock.now = 10.0
    with pytest.raises(ValueError):
        breaker.call(_fail)
    clock.now = 15.0
    assert breaker.state == "open"


def test_breaker_success_resets_failure_count():
    breaker = CircuitBreaker(failure_threshold=2, reset_seconds=10, clock=FakeClock())
    with pytest.raises(ValueError):
        breaker.call(_fail)
    breaker.call(lambda: None)
    with pytest.raises(ValueError):
        breaker.call(_fail)
    assert breaker.state == "closed"


def test_breaker_rejects_invalid_threshold():
    with pytest.raises(ValueError):
        CircuitBreaker(failure_threshold=0)


@pytest.fixture()
def no_backoff(monkeypatch):
    monkeypatch.setattr(settings, "retry_base_delay_seconds", 0.0)
    monkeypatch.setattr(settings, "llm_max_attempts", 3)


def test_resilient_call_retries_transient_errors_and_counts_them(no_backoff):
    provider = ScriptedProvider([TransientError("503"), TransientError("503"), "done"])
    result, usage = generate_with_resilience(provider, "q")
    assert result.text == "done"
    assert (usage.calls, usage.retries) == (3, 2)
    assert (usage.input_tokens, usage.output_tokens) == (100, 20)
    # claude-haiku-5-5: 100 * $0.10/M + 20 * $0.50/M
    assert usage.cost_usd == pytest.approx(0.00002)


def test_resilient_call_does_not_retry_non_transient_errors(no_backoff):
    provider = ScriptedProvider([ValueError("bad request")])
    with pytest.raises(ValueError):
        generate_with_resilience(provider, "q")
    assert len(provider.calls) == 1


def test_resilient_call_gives_up_after_max_attempts(no_backoff):
    provider = ScriptedProvider([TransientError("503")] * 3)
    with pytest.raises(RetryExhaustedError):
        generate_with_resilience(provider, "q")
    assert len(provider.calls) == 3


def test_open_circuit_stops_calls_reaching_the_provider(no_backoff, monkeypatch):
    provider = ScriptedProvider([TransientError("503")] * 10)
    provider.breaker = CircuitBreaker(failure_threshold=3, reset_seconds=60)
    with pytest.raises(RetryExhaustedError):
        generate_with_resilience(provider, "q")
    with pytest.raises(CircuitOpenError):
        generate_with_resilience(provider, "q")
    assert len(provider.calls) == 3
