"""
Integration tests for the multi-agent pipeline (Orchestrator + real agents,
Mock LLM provider throughout).

Maps to docs/test_plan.md: IT-01..IT-05.
"""

from src.agents.base import Agent
from src.agents.planner_agent.agent import PlannerAgent
from src.agents.research_agent.agent import ResearchAgent
from src.agents.validator_agent.agent import ValidatorAgent
from src.orchestrator.main import Orchestrator
from src.shared.schemas import AgentRequest, AgentResponse


def test_full_pipeline_completes_without_exceptions():
    """IT-04: full pipeline executes without exceptions (mocked provider) and returns a result."""
    orchestrator = Orchestrator()
    result = orchestrator.run("Summarize recent advances in multi-agent systems")
    assert result.status == "success"
    assert result.error is None
    assert result.result is not None


def test_pipeline_dispatches_planner_and_research_for_each_subtask():
    """IT-01/IT-02: Orchestrator dispatches to Planner, then Research per sub-task."""
    orchestrator = Orchestrator()
    result = orchestrator.run("Plan a research project")
    step_names = [s.step_name for s in result.steps]
    assert step_names[0] == "planner"
    research_steps = [s for s in step_names if s == "research"]
    assert len(research_steps) == 3  # PlannerAgent default sub_task_count
    assert step_names[-1] == "validator"


def test_pipeline_sends_aggregated_results_to_validator():
    """IT-03: Orchestrator sends aggregated results to Validator, which returns pass/fail."""
    orchestrator = Orchestrator()
    result = orchestrator.run("Aggregate and validate this")
    assert result.result is not None
    assert len(result.result) == 3  # one entry per sub-task, keyed by sub-task id


class _CrashingResearchAgent(Agent):
    """Test double: Research Agent that always raises, to exercise mid-pipeline failure."""

    name = "research_agent"

    def execute(self, request: AgentRequest) -> AgentResponse:
        raise RuntimeError("simulated research crash")


def test_pipeline_handles_agent_failure_mid_execution():
    """
    IT-05: pipeline handles an agent failure mid-execution gracefully.

    A crashing Research Agent means every sub-task result carries an error,
    so the Validator's rule checks correctly reject the aggregate and the
    Orchestrator returns a 'partial' result (after exhausting retries)
    rather than propagating the exception.
    """
    orchestrator = Orchestrator(
        agents={
            "planner": PlannerAgent(),
            "research": _CrashingResearchAgent(),
            "validator": ValidatorAgent(),
        },
        max_retries=2,
    )
    result = orchestrator.run("a task whose research will fail")
    assert result.status == "partial"
    assert result.retries_used == 2
    assert all("error" in v for v in result.result.values())


def test_pipeline_planner_failure_returns_error_without_touching_research():
    """A1 (docs/SRS.md UC-01 Alternate Flow): if Planner fails, Orchestrator returns an error."""

    class _CrashingPlanner(Agent):
        name = "planner_agent"

        def execute(self, request: AgentRequest) -> AgentResponse:
            return AgentResponse(task_id=request.task_id, status="error", error="planner broke")

    orchestrator = Orchestrator(
        agents={
            "planner": _CrashingPlanner(),
            "research": ResearchAgent(),
            "validator": ValidatorAgent(),
        }
    )
    result = orchestrator.run("a task")
    assert result.status == "error"
    assert result.error == "planner broke"
    # Only the planner step should have run; research/validator never dispatched.
    assert [s.step_name for s in result.steps] == ["planner"]
