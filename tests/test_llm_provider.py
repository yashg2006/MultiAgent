"""
Unit tests for the LLM provider abstraction (src/shared/llm_provider.py).

The OpenAI provider is exercised offline by injecting a fake `openai` module
into sys.modules, so no network access or API key is needed and the real
OpenAI SDK need not be installed.
"""

import sys
import types

import pytest

from src.shared.llm_provider import (
    MockLLMProvider,
    OpenAIProvider,
    get_provider,
    safe_json_loads,
)

# --- get_provider factory -----------------------------------------------


def test_get_provider_returns_mock_by_name_case_insensitively():
    assert isinstance(get_provider("mock"), MockLLMProvider)
    assert isinstance(get_provider("  MOCK "), MockLLMProvider)


def test_get_provider_openai_without_key_raises():
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        get_provider("openai", openai_api_key="")


def test_get_provider_unknown_name_raises_value_error():
    with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
        get_provider("not-a-provider")


# --- MockLLMProvider ------------------------------------------------------


def test_mock_complete_is_deterministic_and_prompt_dependent():
    provider = MockLLMProvider()
    assert provider.complete("abc") == provider.complete("abc")
    assert provider.complete("abc") != provider.complete("xyz")


def test_mock_complete_json_returns_structured_dict():
    result = MockLLMProvider().complete_json("plan this", schema_hint="Plan")
    assert result["mock"] is True
    assert result["prompt_excerpt"] == "plan this"
    assert len(result["digest"]) == 8


# --- OpenAIProvider (offline, via a fake `openai` module) -----------------


class _FakeCompletions:
    def __init__(self, recorder: dict) -> None:
        self._recorder = recorder

    def create(self, model: str, messages: list[dict]) -> object:
        self._recorder["model"] = model
        self._recorder["messages"] = messages
        message = types.SimpleNamespace(content="fake completion")
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)])


class _FakeOpenAIClient:
    last_api_key: str | None = None
    recorder: dict = {}

    def __init__(self, api_key: str) -> None:
        _FakeOpenAIClient.last_api_key = api_key
        self.chat = types.SimpleNamespace(completions=_FakeCompletions(_FakeOpenAIClient.recorder))


@pytest.fixture()
def fake_openai(monkeypatch):
    fake_module = types.ModuleType("openai")
    fake_module.OpenAI = _FakeOpenAIClient  # type: ignore[attr-defined]
    _FakeOpenAIClient.recorder = {}
    monkeypatch.setitem(sys.modules, "openai", fake_module)
    return _FakeOpenAIClient


def test_get_provider_openai_with_key_builds_openai_provider(fake_openai):
    provider = get_provider("openai", openai_api_key="sk-test")
    assert isinstance(provider, OpenAIProvider)
    assert fake_openai.last_api_key == "sk-test"


def test_openai_provider_complete_sends_system_and_user_messages(fake_openai):
    provider = OpenAIProvider(api_key="sk-test", model="test-model")
    assert provider.complete("hello", system="be brief") == "fake completion"
    assert fake_openai.recorder["model"] == "test-model"
    assert fake_openai.recorder["messages"] == [
        {"role": "system", "content": "be brief"},
        {"role": "user", "content": "hello"},
    ]


def test_openai_provider_complete_omits_system_message_when_not_given(fake_openai):
    OpenAIProvider(api_key="sk-test").complete("hello")
    assert fake_openai.recorder["messages"] == [{"role": "user", "content": "hello"}]


# --- safe_json_loads -------------------------------------------------------


def test_safe_json_loads_parses_json_object():
    assert safe_json_loads('{"a": 1}') == {"a": 1}


@pytest.mark.parametrize("bad_input", ["not json", "[1, 2, 3]", None])
def test_safe_json_loads_returns_none_for_invalid_or_non_object(bad_input):
    assert safe_json_loads(bad_input) is None
