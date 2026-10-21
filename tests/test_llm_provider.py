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


# --- Phase F1: generate(), Anthropic, structured mock output, costing ----------

import json  # noqa: E402

from src.shared import llm_provider  # noqa: E402
from src.shared.config import settings  # noqa: E402
from src.shared.llm_provider import (  # noqa: E402
    AnthropicProvider,
    estimate_cost,
    extract_json_object,
    provider_from_settings,
    reset_provider_cache,
)


def test_mock_plan_output_is_valid_json_honouring_the_requested_limit():
    text = (
        MockLLMProvider()
        .generate("Objective: Learn EDF\nReturn at most 4 sub-tasks", kind="plan")
        .text
    )
    subs = json.loads(text)["sub_tasks"]
    assert len(subs) == 4
    assert subs[0]["description"] == "Research aspect 1 of: Learn EDF"
    assert subs[-1]["depends_on"] == ["st-1"]


def test_mock_judge_output_is_a_passing_score():
    verdict = json.loads(MockLLMProvider().generate("x", kind="judge").text)
    assert verdict["score"] == 1.0


def test_mock_reports_zero_tokens():
    result = MockLLMProvider().generate("hello")
    assert (result.input_tokens, result.output_tokens) == (0, 0)


class _FakeAnthropicMessages:
    def __init__(self, recorder):
        self._recorder = recorder

    def create(self, **kwargs):
        self._recorder["create"] = kwargs
        return types.SimpleNamespace(
            content=[
                types.SimpleNamespace(type="text", text="Hello "),
                types.SimpleNamespace(type="tool_use"),
                types.SimpleNamespace(type="text", text="there"),
            ],
            usage=types.SimpleNamespace(input_tokens=42, output_tokens=7),
        )


@pytest.fixture()
def fake_anthropic(monkeypatch):
    recorder: dict = {}
    module = types.ModuleType("anthropic")

    class Anthropic:
        def __init__(self, **kwargs):
            recorder["client"] = kwargs
            self.messages = _FakeAnthropicMessages(recorder)

    class APIConnectionError(Exception):
        pass

    class RateLimitError(Exception):
        pass

    class InternalServerError(Exception):
        pass

    module.Anthropic = Anthropic  # type: ignore[attr-defined]
    module.APIConnectionError = APIConnectionError  # type: ignore[attr-defined]
    module.RateLimitError = RateLimitError  # type: ignore[attr-defined]
    module.InternalServerError = InternalServerError  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "anthropic", module)
    return recorder, module


def test_anthropic_provider_disables_sdk_retries_and_sets_timeout(fake_anthropic):
    recorder, _ = fake_anthropic
    AnthropicProvider(api_key="sk-ant-test", model="claude-haiku-5-5", timeout=12.0)
    assert recorder["client"] == {"api_key": "sk-ant-test", "timeout": 12.0, "max_retries": 0}


def test_anthropic_provider_generate_joins_text_blocks_and_reports_usage(fake_anthropic):
    recorder, _ = fake_anthropic
    provider = AnthropicProvider(api_key="k", model="claude-haiku-5-5")
    result = provider.generate("hi", system="be brief", max_tokens=50)
    assert result.text == "Hello there"
    assert (result.input_tokens, result.output_tokens) == (42, 7)
    assert recorder["create"] == {
        "model": "claude-haiku-5-5",
        "max_tokens": 50,
        "messages": [{"role": "user", "content": "hi"}],
        "system": "be brief",
    }


def test_anthropic_provider_retries_only_transient_error_types(fake_anthropic):
    _, module = fake_anthropic
    provider = AnthropicProvider(api_key="k")
    assert set(provider.retryable_errors) == {
        module.APIConnectionError,
        module.RateLimitError,
        module.InternalServerError,
    }


def test_get_provider_anthropic_requires_key():
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        get_provider("anthropic")


def test_get_provider_anthropic_uses_configured_model(fake_anthropic, monkeypatch):
    monkeypatch.setattr(settings, "anthropic_model", "claude-sonnet-5-5")
    provider = get_provider("anthropic", anthropic_api_key="k")
    assert provider.model == "claude-sonnet-5-5"


def test_estimate_cost_uses_price_table_and_zero_for_unknown_models():
    assert estimate_cost("claude-haiku-5-5", 1_000_000, 1_000_000) == pytest.approx(0.60)
    assert estimate_cost("claude-sonnet-5-5", 1000, 0) == pytest.approx(0.002)
    assert estimate_cost("mystery-model", 10, 10) == 0.0


def test_provider_from_settings_is_shared_until_reset(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "mock")
    reset_provider_cache()
    first = provider_from_settings()
    assert provider_from_settings() is first
    reset_provider_cache()
    assert provider_from_settings() is not first
    assert llm_provider._provider_cache  # repopulated


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('{"a": 1}', {"a": 1}),
        ('Sure!\n```json\n{"a": 2}\n```', {"a": 2}),
        ('Result: {"a": 3} hope that helps', {"a": 3}),
        ("no json here", None),
        ("[1, 2]", None),
    ],
)
def test_extract_json_object(text, expected):
    assert extract_json_object(text) == expected
