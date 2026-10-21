"""Search tools for the Research Agent (no real network access)."""

import io
import json

import pytest

from src.agents.research_agent.agent import ResearchAgent
from src.shared.schemas import AgentRequest
from src.shared.search import (
    NullSearchTool,
    SearchHit,
    SearchTool,
    WikipediaSearchTool,
    get_search_tool,
)
from tests.fakes import ScriptedProvider


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def wikipedia_payload(*titles):
    return json.dumps(
        {
            "query": {
                "search": [
                    {"title": t, "snippet": f'<span class="searchmatch">{t}</span> &amp; more'}
                    for t in titles
                ]
            }
        }
    ).encode()


def test_wikipedia_tool_parses_hits_and_strips_markup():
    requests = []

    def opener(request, timeout):
        requests.append((request, timeout))
        return FakeResponse(wikipedia_payload("Earliest deadline first scheduling"))

    hits = WikipediaSearchTool(timeout=5, opener=opener).search("EDF scheduling")
    assert hits[0].title == "Earliest deadline first scheduling"
    assert hits[0].snippet == "Earliest deadline first scheduling & more"
    assert hits[0].url == "https://en.wikipedia.org/wiki/Earliest_deadline_first_scheduling"
    request, timeout = requests[0]
    assert "srsearch=EDF+scheduling" in request.full_url
    assert request.get_header("User-agent").startswith("MultiAgentAISystem")
    assert timeout == 5


def test_wikipedia_tool_returns_no_hits_on_network_error():
    def opener(request, timeout):
        raise OSError("network unreachable")

    assert WikipediaSearchTool(opener=opener).search("anything") == []


def test_wikipedia_tool_returns_no_hits_on_unexpected_payload():
    def opener(request, timeout):
        return FakeResponse(b'{"error": "nope"}')

    assert WikipediaSearchTool(opener=opener).search("anything") == []


def test_wikipedia_tool_skips_blank_queries():
    def opener(request, timeout):
        raise AssertionError("should not be called")

    assert WikipediaSearchTool(opener=opener).search("   ") == []


def test_get_search_tool_by_name():
    assert isinstance(get_search_tool("none"), NullSearchTool)
    assert isinstance(get_search_tool("Wikipedia"), WikipediaSearchTool)
    with pytest.raises(ValueError):
        get_search_tool("bing")


class StaticSearch(SearchTool):
    def search(self, query, limit=3):
        return [SearchHit(title="EDF", snippet="deadline-driven", url="https://x/EDF")]


def test_research_agent_grounds_prompt_in_search_hits_and_returns_sources():
    provider = ScriptedProvider(["EDF schedules by deadline."])
    agent = ResearchAgent(provider=provider, search_tool=StaticSearch())
    response = agent.execute(AgentRequest(task_id="t", prompt="What is EDF?"))
    prompt = provider.calls[0]["prompt"]
    assert "Question: What is EDF?" in prompt
    assert "EDF: deadline-driven (https://x/EDF)" in prompt
    assert response.result["sources"] == [{"title": "EDF", "url": "https://x/EDF"}]
    assert response.usage.calls == 1


def test_research_agent_includes_dependency_context_and_retry_feedback():
    provider = ScriptedProvider(["answer"])
    agent = ResearchAgent(provider=provider, search_tool=NullSearchTool())
    agent.execute(
        AgentRequest(
            task_id="t",
            prompt="Compare them",
            metadata={"context": {"st-1": "EDF is optimal"}, "feedback": ["too vague"]},
        )
    )
    prompt = provider.calls[0]["prompt"]
    assert "- [st-1] EDF is optimal" in prompt
    assert "- too vague" in prompt
