"""
Unit tests for the Orchestrator.

Maps to docs/test_plan.md: UT-O-*.
"""

from src.agents.base import Agent
from src.agents.planner_agent.agent import PlannerAgent
from src.agents.research_agent.agent import ResearchAgent
from src.agents.validator_agent.agent import ValidatorAgent
from src.orchestrator.main import Orchestrator
from src.shared.schemas import AgentRequest, AgentResponse


class _AlwaysFailValidator(Agent):
    """Test double: a Validator stand-in that always rejects, to exercise retry/partial-result."""

    name = "validator_agent"

    def execute(self, request: AgentRequest) -> AgentResponse:
        return AgentResponse(
            task_id=request.task_id,
            status="rejected",
            result={
                "validation": {
                    "status": "fail",
                    "score": 0.0,
                    "reasons": ["forced failure for testing"],
                }
            },
        )


class _CrashingAgent(Agent):
    """Test double: an agent whose execute() raises, to exercise orchestrator resilience."""

    name = "planner_agent"

    def execute(self, request: AgentRequest) -> AgentResponse:
        raise RuntimeError("simulated agent crash")


def test_orchestrator_initialises_without_errors():
    """UT-O-01: Orchestrator initialises without errors, with default agents."""
    orchestrator = Orchestrator()
    assert orchestrator is not None
    assert set(orchestrator.agents.keys()) == {"planner", "research", "validator"}


def test_orchestrator_run_returns_success_for_valid_task():
    """UT-O-02: run() returns a successful RunResult for a valid task."""
    orchestrator = Orchestrator()
    result = orchestrator.run("sample task")
    assert result.status == "success"
    assert result.result is not None
    assert result.retries_used == 0
    assert len(result.steps) >= 3  # planner + >=1 research + validator


def test_orchestrator_run_handles_empty_input_gracefully():
    """UT-O-03: run() handles empty input gracefully (error, not a crash)."""
    orchestrator = Orchestrator()
    result = orchestrator.run("")
    assert result.status == "error"
    assert result.error is not None


def test_orchestrator_retries_on_validation_failure_then_returns_partial():
    """UT-O-04: retry logic triggers on validation failure, up to max_retries, then partial."""
    orchestrator = Orchestrator(
        agents={
            "planner": PlannerAgent(),
            "research": ResearchAgent(),
            "validator": _AlwaysFailValidator(),
        },
        max_retries=2,
    )
    result = orchestrator.run("sample task")
    assert result.status == "partial"
    assert result.retries_used == 2
    assert "forced failure" in (result.error or "")


def test_orchestrator_handles_crashing_agent_without_raising():
    """A crashing agent must not crash the Orchestrator; it should surface as an error step."""
    orchestrator = Orchestrator(
        agents={
            "planner": _CrashingAgent(),
            "research": ResearchAgent(),
            "validator": ValidatorAgent(),
        }
    )
    result = orchestrator.run("sample task")
    assert result.status == "error"
    assert "simulated agent crash" in (result.error or "")
