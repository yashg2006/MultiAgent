"""
Unit tests for individual agents (ResearchAgent, PlannerAgent, ValidatorAgent).

All agents default to the Mock LLM provider (src/shared/llm_provider.py),
so these tests run deterministically offline with no API key.

Maps to docs/test_plan.md: UT-R-*, UT-P-*, UT-V-*.
"""

from src.agents.planner_agent.agent import PlannerAgent
from src.agents.research_agent.agent import ResearchAgent
from src.agents.validator_agent.agent import ValidatorAgent
from src.shared.schemas import AgentRequest, ValidationStatus

# --- Research Agent ---------------------------------------------------


def test_research_agent_execute_returns_success():
    """UT-R-01: execute() returns a successful AgentResponse with findings."""
    agent = ResearchAgent()
    response = agent.execute(AgentRequest(task_id="t1", prompt="test query"))
    assert response.status == "success"
    assert response.result is not None
    assert response.result["query"] == "test query"
    assert "findings" in response.result


def test_research_agent_execute_is_deterministic():
    """The Mock provider must be a pure function of the prompt text."""
    agent = ResearchAgent()
    r1 = agent.execute(AgentRequest(task_id="t1", prompt="same query"))
    r2 = agent.execute(AgentRequest(task_id="t2", prompt="same query"))
    assert r1.result["findings"] == r2.result["findings"]


def test_research_agent_rejects_empty_query():
    """UT-R-02: execute() handles an empty query by returning an error, not raising."""
    agent = ResearchAgent()
    response = agent.execute(AgentRequest(task_id="t1", prompt=""))
    assert response.status == "error"
    assert response.error is not None


def test_research_agent_initialises_without_config():
    """UT-R-04: agent initialises with config=None (defaults applied)."""
    agent = ResearchAgent()
    assert agent.config == {}
    assert agent.provider is not None


# --- Planner Agent ------------------------------------------------------


def test_planner_agent_create_plan_returns_plan_with_subtasks():
    """UT-P-01/02: create_plan() returns a Plan with structured sub-tasks."""
    agent = PlannerAgent()
    plan = agent.create_plan("test objective")
    assert plan.objective == "test objective"
    assert len(plan.sub_tasks) == 3
    for sub_task in plan.sub_tasks:
        assert sub_task.id
        assert sub_task.description


def test_planner_agent_create_plan_respects_sub_task_count_config():
    agent = PlannerAgent(config={"sub_task_count": 5})
    plan = agent.create_plan("another objective")
    assert len(plan.sub_tasks) == 5


def test_planner_agent_execute_wraps_plan_in_agent_response():
    agent = PlannerAgent()
    response = agent.execute(AgentRequest(task_id="t1", prompt="complex objective"))
    assert response.status == "success"
    assert "plan" in response.result
    assert response.result["plan"]["sub_tasks"]


def test_planner_agent_rejects_empty_objective():
    """UT-P-03: create_plan()/execute() handles empty input as an error."""
    agent = PlannerAgent()
    response = agent.execute(AgentRequest(task_id="t1", prompt=""))
    assert response.status == "error"


# --- Validator Agent ------------------------------------------------------


def test_validator_agent_validate_passes_for_valid_data():
    """UT-V-01: validate() returns PASS for well-formed, non-empty results."""
    agent = ValidatorAgent()
    result = agent.validate({"st-1": {"findings": "some data"}})
    assert result.status == ValidationStatus.PASS


def test_validator_agent_validate_fails_for_empty_subtask():
    """UT-V-02: validate() returns FAIL when a sub-task entry is empty."""
    agent = ValidatorAgent()
    result = agent.validate({"st-1": {}, "st-2": {"findings": "ok"}})
    assert result.status == ValidationStatus.FAIL
    assert any("st-1" in r for r in result.reasons)


def test_validator_agent_validate_fails_for_upstream_error():
    agent = ValidatorAgent()
    result = agent.validate({"st-1": {"error": "research failed"}})
    assert result.status == ValidationStatus.FAIL
    assert any("error" in r for r in result.reasons)


def test_validator_agent_validate_fails_for_empty_dict():
    """UT-V-03: validate() handles an empty dict as a failure (nothing to validate)."""
    agent = ValidatorAgent()
    result = agent.validate({})
    assert result.status == ValidationStatus.FAIL


def test_validator_agent_execute_requires_results_in_metadata():
    agent = ValidatorAgent()
    response = agent.execute(AgentRequest(task_id="t1", prompt="validate"))
    assert response.status == "error"


def test_validator_agent_execute_returns_rejected_on_failed_validation():
    agent = ValidatorAgent()
    response = agent.execute(
        AgentRequest(
            task_id="t1",
            prompt="validate",
            metadata={"results": {"st-1": {}}},
        )
    )
    assert response.status == "rejected"
