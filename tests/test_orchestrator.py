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


# --- Phase F1: dependency ordering, streaming, cancellation, usage -------------

import json  # noqa: E402

from src.orchestrator.main import dependency_levels  # noqa: E402
from src.shared.search import NullSearchTool  # noqa: E402
from tests.fakes import ScriptedProvider  # noqa: E402


def test_dependency_levels_orders_by_dependencies_and_keeps_plan_order():
    subs = [
        {"id": "a", "depends_on": ["c"]},
        {"id": "b", "depends_on": []},
        {"id": "c", "depends_on": []},
    ]
    assert [[s["id"] for s in lvl] for lvl in dependency_levels(subs)] == [["b", "c"], ["a"]]


def test_dependency_levels_breaks_cycles_instead_of_hanging():
    subs = [{"id": "a", "depends_on": ["b"]}, {"id": "b", "depends_on": ["a"]}]
    assert [[s["id"] for s in lvl] for lvl in dependency_levels(subs)] == [["a", "b"]]


def _scripted_orchestrator(plan, research_answer="answer", judge_score=0.9):
    def respond(prompt, kind):
        if kind == "plan":
            return json.dumps({"sub_tasks": plan})
        if kind == "judge":
            return json.dumps({"score": judge_score, "reasons": ["ok"]})
        return f"{research_answer} for: {prompt.splitlines()[0]}"

    provider = ScriptedProvider(respond)
    agents = {
        "planner": PlannerAgent(provider=provider),
        "research": ResearchAgent(provider=provider, search_tool=NullSearchTool()),
        "validator": ValidatorAgent(provider=provider),
    }
    return Orchestrator(agents=agents, max_retries=2), provider


def test_dependent_sub_task_receives_findings_of_its_dependencies():
    plan = [
        {"id": "st-1", "description": "What is EDF?", "depends_on": []},
        {"id": "st-2", "description": "Compare with RMS", "depends_on": ["st-1"]},
    ]
    orchestrator, provider = _scripted_orchestrator(plan)
    result = orchestrator.run("Compare EDF and RMS")
    assert result.status == "success"
    st2_prompt = next(c["prompt"] for c in provider.calls if "Compare with RMS" in c["prompt"])
    assert "[st-1] answer for: What is EDF?" in st2_prompt
    assert [s.sub_task_id for s in result.steps if s.step_name == "research"] == ["st-1", "st-2"]


def test_on_step_streams_every_step_and_usage_is_totalled():
    plan = [{"id": "st-1", "description": "Q1", "depends_on": []}]
    orchestrator, _ = _scripted_orchestrator(plan)
    streamed = []
    result = orchestrator.run("goal", on_step=streamed.append)
    assert [s.step_name for s in streamed] == ["planner", "research", "validator"]
    assert result.usage.calls == 3
    assert result.usage.input_tokens == 300
    assert result.usage.cost_usd > 0


def test_failing_on_step_callback_does_not_break_the_run():
    plan = [{"id": "st-1", "description": "Q1", "depends_on": []}]
    orchestrator, _ = _scripted_orchestrator(plan)

    def broken(step):
        raise RuntimeError("observer crashed")

    assert orchestrator.run("goal", on_step=broken).status == "success"


def test_cancellation_stops_between_stages_and_keeps_partial_results():
    plan = [
        {"id": "st-1", "description": "Q1", "depends_on": []},
        {"id": "st-2", "description": "Q2", "depends_on": ["st-1"]},
    ]
    orchestrator, _ = _scripted_orchestrator(plan)
    checks = {"n": 0}

    def cancel_on_second_check():
        checks["n"] += 1
        return checks["n"] >= 2

    result = orchestrator.run("goal", should_cancel=cancel_on_second_check)
    assert result.status == "cancelled"
    assert list(result.result) == ["st-1"]
    assert [s.step_name for s in result.steps] == ["planner", "research"]


def test_retry_passes_validator_feedback_to_research():
    plan = [{"id": "st-1", "description": "Q1", "depends_on": []}]
    orchestrator, provider = _scripted_orchestrator(plan, judge_score=0.1)
    result = orchestrator.run("goal")
    assert result.status == "partial"
    research_prompts = [c["prompt"] for c in provider.calls if c["kind"] == "text"]
    assert "rejected" not in research_prompts[0]
    assert "A reviewer rejected the previous answers" in research_prompts[1]


def test_run_uses_supplied_task_id():
    assert Orchestrator().run("goal", task_id="fixed-id").task_id == "fixed-id"
