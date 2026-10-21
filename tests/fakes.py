"""Test doubles shared across test modules."""

from __future__ import annotations

from collections.abc import Callable

from src.shared.llm_provider import LLMProvider, LLMResult


class TransientError(Exception):
    """Stands in for a provider's retryable error (e.g. HTTP 503)."""


class ScriptedProvider(LLMProvider):
    """Returns scripted responses in order and records every call.

    Each script item is either a string (returned as the response text) or an
    exception instance (raised). A callable script receives (prompt, kind).
    """

    model = "claude-haiku-5-5"

    def __init__(
        self,
        script: list[str | Exception] | Callable[[str, str], str] | None = None,
        *,
        tokens: tuple[int, int] = (100, 20),
    ) -> None:
        super().__init__()
        self.retryable_errors = (TransientError,)
        self._script = script if script is not None else []
        self._tokens = tokens
        self.calls: list[dict] = []

    def generate(self, prompt, *, system=None, max_tokens=1024, kind="text") -> LLMResult:
        self.calls.append({"prompt": prompt, "system": system, "kind": kind})
        if callable(self._script):
            item: str | Exception = self._script(prompt, kind)
        else:
            if not self._script:
                raise AssertionError("ScriptedProvider ran out of responses")
            item = self._script.pop(0)
        if isinstance(item, Exception):
            raise item
        return LLMResult(
            text=item, input_tokens=self._tokens[0], output_tokens=self._tokens[1], model=self.model
        )
