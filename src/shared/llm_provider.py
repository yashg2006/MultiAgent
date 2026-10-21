"""
LLM provider abstraction.

Agents never talk to a vendor SDK directly. They call
`generate_with_resilience(provider, ...)`, which runs the provider's
`generate()` through a circuit breaker and retries transient errors with
exponential backoff (NFR-03), and returns token usage and cost alongside the
text.

Providers:
- `MockLLMProvider` (default): deterministic and offline, so tests, CI, and
  demos need no API key. It understands the structured-output kinds the
  agents ask for ("plan", "judge") and returns valid JSON for them.
- `AnthropicProvider`: Claude via the `anthropic` SDK (`LLM_PROVIDER=anthropic`).
- `OpenAIProvider`: via the `openai` SDK (`LLM_PROVIDER=openai`).
Vendor SDKs are imported only when their provider is constructed.
"""

from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from src.shared.config import MODEL_PRICES_PER_MTOK, settings
from src.shared.resilience import CircuitBreaker
from src.shared.retry import call_with_retry
from src.shared.schemas import LLMUsage
from src.shared.utils import setup_logger

logger = setup_logger(__name__)

# What the caller expects back. Real models are steered by the system prompt;
# the Mock uses this to return well-formed output of the right shape.
KINDS = ("text", "plan", "judge")


class LLMResult(BaseModel):
    """One model response plus its token usage."""

    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""


class LLMProvider(ABC):
    """Common interface every LLM backend implements."""

    name: str = "base"
    model: str = "unknown"

    def __init__(self) -> None:
        self.breaker = CircuitBreaker(
            failure_threshold=settings.circuit_failure_threshold,
            reset_seconds=settings.circuit_reset_seconds,
        )
        # Exception types worth retrying (network errors, rate limits, 5xx).
        self.retryable_errors: tuple[type[Exception], ...] = ()

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        kind: str = "text",
    ) -> LLMResult:
        """Return the model's response to `prompt`."""
        raise NotImplementedError

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        """Convenience wrapper returning only the text."""
        return self.generate(prompt, system=system).text


class MockLLMProvider(LLMProvider):
    """
    Deterministic, offline stand-in for a real LLM.

    Output is a pure function of the input, so the same prompt always gives
    the same response. Token counts are reported as 0: nothing is billed, and
    inventing counts would make the metrics misleading.
    """

    name = "mock"
    model = "mock"

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        kind: str = "text",
    ) -> LLMResult:
        if settings.mock_latency_seconds > 0:
            time.sleep(settings.mock_latency_seconds)
        if kind == "plan":
            text = self._plan(prompt)
        elif kind == "judge":
            text = json.dumps({"score": 1.0, "reasons": ["Mock judge: rule checks decide."]})
        else:
            digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8]
            text = f"[mock-response:{digest}] {prompt[:120]}"
        return LLMResult(text=text, model=self.model)

    @staticmethod
    def _plan(prompt: str) -> str:
        """A plan with as many sub-tasks as the prompt allows; the last depends
        on the first, so dependency ordering is exercised offline too."""
        objective_match = re.search(r"Objective:\s*(.+)", prompt)
        objective = objective_match.group(1).strip() if objective_match else prompt.strip()
        count_match = re.search(r"at most (\d+) sub-tasks", prompt)
        count = int(count_match.group(1)) if count_match else 3
        sub_tasks = [
            {
                "id": f"st-{i}",
                "description": f"Research aspect {i} of: {objective}",
                "depends_on": ["st-1"] if i == count and count >= 3 else [],
            }
            for i in range(1, count + 1)
        ]
        return json.dumps({"sub_tasks": sub_tasks})

    def complete_json(self, prompt: str, *, schema_hint: str = "") -> dict[str, Any]:
        """Deterministic structured completion (kept for backwards compatibility)."""
        digest = hashlib.sha256((prompt + schema_hint).encode("utf-8")).hexdigest()[:8]
        return {"mock": True, "digest": digest, "prompt_excerpt": prompt[:80]}


class AnthropicProvider(LLMProvider):
    """Claude via the official `anthropic` SDK.

    The SDK's own retries are disabled (`max_retries=0`) so every retry goes
    through `generate_with_resilience`, where it is counted and backed off
    consistently with the rest of the system.
    """

    name = "anthropic"

    def __init__(self, api_key: str, model: str = "claude-haiku-5-5", timeout: float = 60.0):
        super().__init__()
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - only without the optional dep
            raise RuntimeError(
                "LLM_PROVIDER=anthropic requires the 'anthropic' package "
                "(pip install anthropic) or set LLM_PROVIDER=mock."
            ) from exc
        self._client = anthropic.Anthropic(api_key=api_key, timeout=timeout, max_retries=0)
        self.model = model
        self.retryable_errors = tuple(
            err
            for err in (
                getattr(anthropic, "APIConnectionError", None),  # incl. timeouts
                getattr(anthropic, "RateLimitError", None),  # 429
                getattr(anthropic, "InternalServerError", None),  # 5xx, incl. overloaded
            )
            if isinstance(err, type)
        )

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        kind: str = "text",
    ) -> LLMResult:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        message = self._client.messages.create(**kwargs)
        text = "".join(
            block.text for block in message.content if getattr(block, "type", None) == "text"
        )
        return LLMResult(
            text=text,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
            model=self.model,
        )


class OpenAIProvider(LLMProvider):
    """OpenAI chat completions via the `openai` SDK."""

    name = "openai"

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        super().__init__()
        try:
            import openai
        except ImportError as exc:  # pragma: no cover - only without the optional dep
            raise RuntimeError(
                "LLM_PROVIDER=openai requires the 'openai' package. "
                "Install it with `pip install openai` or set LLM_PROVIDER=mock."
            ) from exc
        self._client = openai.OpenAI(api_key=api_key)
        self.model = model
        self.retryable_errors = tuple(
            err
            for err in (
                getattr(openai, "APIConnectionError", None),
                getattr(openai, "RateLimitError", None),
                getattr(openai, "InternalServerError", None),
            )
            if isinstance(err, type)
        )

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        kind: str = "text",
    ) -> LLMResult:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
        )
        usage = getattr(response, "usage", None)
        return LLMResult(
            text=response.choices[0].message.content or "",
            input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            output_tokens=getattr(usage, "completion_tokens", 0) or 0,
            model=self.model,
        )


def get_provider(
    provider_name: str,
    openai_api_key: str = "",
    *,
    anthropic_api_key: str = "",
) -> LLMProvider:
    """Build a new provider by name ("mock", "anthropic", or "openai")."""
    normalized = provider_name.strip().lower()
    if normalized == "mock":
        return MockLLMProvider()
    if normalized == "anthropic":
        if not anthropic_api_key:
            raise RuntimeError(
                "LLM_PROVIDER=anthropic requires ANTHROPIC_API_KEY to be set in the environment."
            )
        return AnthropicProvider(
            api_key=anthropic_api_key,
            model=settings.anthropic_model,
            timeout=settings.llm_timeout_seconds,
        )
    if normalized == "openai":
        if not openai_api_key:
            raise RuntimeError(
                "LLM_PROVIDER=openai requires OPENAI_API_KEY to be set in the environment."
            )
        return OpenAIProvider(api_key=openai_api_key, model=settings.openai_model)
    raise ValueError(
        f"Unknown LLM_PROVIDER: {provider_name!r} (expected 'mock', 'anthropic', or 'openai')"
    )


_provider_cache: dict[str, LLMProvider] = {}
_provider_cache_lock = threading.Lock()


def provider_from_settings() -> LLMProvider:
    """The configured provider, shared process-wide.

    Sharing matters: the circuit breaker only protects the system if every
    agent and every run sees the same failure history, and SDK clients reuse
    their HTTP connection pools.
    """
    key = settings.llm_provider.strip().lower()
    with _provider_cache_lock:
        if key not in _provider_cache:
            _provider_cache[key] = get_provider(
                key,
                settings.openai_api_key,
                anthropic_api_key=settings.anthropic_api_key,
            )
        return _provider_cache[key]


def reset_provider_cache() -> None:
    """Forget shared providers (used by tests and after config changes)."""
    with _provider_cache_lock:
        _provider_cache.clear()


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """USD cost of one call from the price table in `src/shared/config.py`."""
    prices = MODEL_PRICES_PER_MTOK.get(model)
    if prices is None:
        if input_tokens or output_tokens:
            logger.warning("No price configured for model %r; costing it at $0", model)
        return 0.0
    input_price, output_price = prices
    return round((input_tokens * input_price + output_tokens * output_price) / 1_000_000, 8)


def generate_with_resilience(
    provider: LLMProvider,
    prompt: str,
    *,
    system: str | None = None,
    kind: str = "text",
    max_tokens: int | None = None,
) -> tuple[LLMResult, LLMUsage]:
    """Call the provider through its circuit breaker, retrying transient errors.

    Returns the response and its usage (calls, retries, tokens, cost).
    Non-retryable errors (bad request, auth, open circuit) propagate at once;
    if every attempt fails, `RetryExhaustedError` is raised.
    """
    retries = 0

    def count_retry(_attempt: int, _error: Exception) -> None:
        nonlocal retries
        retries += 1

    def attempt() -> LLMResult:
        return provider.breaker.call(
            lambda: provider.generate(
                prompt,
                system=system,
                kind=kind,
                max_tokens=max_tokens or settings.llm_max_tokens,
            )
        )

    result = call_with_retry(
        attempt,
        max_retries=settings.llm_max_attempts,
        base_delay_seconds=settings.retry_base_delay_seconds,
        retry_on=provider.retryable_errors,
        on_retry=count_retry,
    )
    usage = LLMUsage(
        calls=retries + 1,
        retries=retries,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        cost_usd=estimate_cost(result.model, result.input_tokens, result.output_tokens),
    )
    return result, usage


def safe_json_loads(text: str) -> dict[str, Any] | None:
    """Best-effort JSON parse that never raises; returns None on failure."""
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def extract_json_object(text: str) -> dict[str, Any] | None:
    """Parse a JSON object from model output that may be wrapped in prose or
    Markdown code fences. Returns None if no object can be parsed."""
    if not isinstance(text, str):
        return None
    direct = safe_json_loads(text.strip())
    if direct is not None:
        return direct
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        parsed = safe_json_loads(fenced.group(1))
        if parsed is not None:
            return parsed
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        return safe_json_loads(text[start : end + 1])
    return None
