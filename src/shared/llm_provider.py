"""
LLM provider abstraction.

Agents call `get_provider()` to obtain an `LLMProvider` without knowing which
concrete backend is in use. Selection is via the `LLM_PROVIDER` environment
variable (see `src/shared/config.py`), defaulting to "mock" so the whole
pipeline runs deterministically offline with no API key — required for CI
and for anyone without an LLM API key to run the test suite.
"""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """Common interface every LLM backend must implement."""

    @abstractmethod
    def complete(self, prompt: str, *, system: str | None = None) -> str:
        """Return a text completion for the given prompt."""
        raise NotImplementedError


class MockLLMProvider(LLMProvider):
    """
    Deterministic, offline stand-in for a real LLM.

    Behaviour is a pure function of the prompt text (via a hash), so the same
    input always produces the same output — essential for repeatable tests
    and for running demos without an API key or network access.
    """

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8]
        return f"[mock-response:{digest}] {prompt[:120]}"

    def complete_json(self, prompt: str, *, schema_hint: str = "") -> dict[str, Any]:
        """
        Deterministic structured completion, used by agents that need a
        parseable result (e.g. the Planner Agent's sub-task list) rather
        than free text.
        """
        digest = hashlib.sha256((prompt + schema_hint).encode("utf-8")).hexdigest()[:8]
        return {"mock": True, "digest": digest, "prompt_excerpt": prompt[:80]}


class OpenAIProvider(LLMProvider):
    """
    Real OpenAI-backed provider. Only imports the `openai` SDK when
    instantiated, so it never becomes a hard dependency for Mock-only usage
    (tests, CI, and anyone without an API key).
    """

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - exercised only without the optional dep
            raise RuntimeError(
                "LLM_PROVIDER=openai requires the 'openai' package. "
                "Install it with `pip install openai` or set LLM_PROVIDER=mock."
            ) from exc
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
        )
        return response.choices[0].message.content or ""


def get_provider(provider_name: str, openai_api_key: str = "") -> LLMProvider:
    """
    Factory returning the configured LLMProvider.

    Args:
        provider_name: one of "mock" or "openai" (more may be added later;
            ask before adding a paid provider per project rules).
        openai_api_key: required when provider_name == "openai".
    """
    normalized = provider_name.strip().lower()
    if normalized == "mock":
        return MockLLMProvider()
    if normalized == "openai":
        if not openai_api_key:
            raise RuntimeError(
                "LLM_PROVIDER=openai requires OPENAI_API_KEY to be set in the environment."
            )
        return OpenAIProvider(api_key=openai_api_key)
    raise ValueError(f"Unknown LLM_PROVIDER: {provider_name!r} (expected 'mock' or 'openai')")


def safe_json_loads(text: str) -> dict[str, Any] | None:
    """Best-effort JSON parse that never raises; returns None on failure."""
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None
