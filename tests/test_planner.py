"""Planner Agent: parsing real-model output into a valid, dependency-aware Plan."""

import json

import pytest

from src.agents.planner_agent.agent import PlanError, PlannerAgent, validate_plan_structure
from src.shared.schemas import AgentRequest, SubTask
from tests.fakes import ScriptedProvider


def plan_json(*sub_tasks: tuple[str, list[str]]) -> str:
    return json.dumps(
        {
            "sub_tasks": [
                {"id": sid, "description": f"Question {sid}", "depends_on": deps}
                for sid, deps in sub_tasks
            ]
        }
    )


def test_parses_plan_wrapped_in_prose_and_code_fences():
    text = "Here is the plan:\n```json\n" + plan_json(("st-1", []), ("st-2", ["st-1"])) + "\n```"
    agent = PlannerAgent(provider=ScriptedProvider([text]))
    plan, usage = agent.create_plan_with_usage("objective")
    assert [s.id for s in plan.sub_tasks] == ["st-1", "st-2"]
    assert plan.sub_tasks[1].depends_on == ["st-1"]
    assert usage.calls == 1


def test_prompt_states_the_sub_task_limit_and_asks_for_plan_output():
    provider = ScriptedProvider([plan_json(("st-1", []))])
    PlannerAgent(provider=provider, config={"sub_task_count": 4}).create_plan("objective")
    assert "at most 4 sub-tasks" in provider.calls[0]["prompt"]
    assert provider.calls[0]["kind"] == "plan"


def test_invalid_output_triggers_one_repair_attempt_with_the_problem():
    provider = ScriptedProvider(["not json at all", plan_json(("st-1", []))])
    plan, usage = PlannerAgent(provider=provider).create_plan_with_usage("objective")
    assert len(plan.sub_tasks) == 1
    assert usage.calls == 2
    assert "not usable" in provider.calls[1]["prompt"]


def test_gives_up_after_the_repair_attempt_and_reports_an_error():
    provider = ScriptedProvider(["nope", "still nope"])
    response = PlannerAgent(provider=provider).execute(AgentRequest(task_id="t", prompt="obj"))
    assert response.status == "error"
    assert response.error.startswith("Planning failed:")


def test_provider_failure_is_reported_not_raised():
    provider = ScriptedProvider([ValueError("auth failed")])
    response = PlannerAgent(provider=provider).execute(AgentRequest(task_id="t", prompt="obj"))
    assert response.status == "error"
    assert "auth failed" in response.error


@pytest.mark.parametrize(
    ("sub_tasks", "message"),
    [
        ([], "no sub-tasks"),
        ([SubTask(id="a", description="x"), SubTask(id="a", description="y")], "unique"),
        ([SubTask(id="a", description="x", depends_on=["zzz"])], "unknown ids"),
        ([SubTask(id="a", description="x", depends_on=["a"])], "itself"),
        (
            [
                SubTask(id="a", description="x", depends_on=["b"]),
                SubTask(id="b", description="y", depends_on=["a"]),
            ],
            "Circular",
        ),
        ([SubTask(id="a", description="   ")], "empty description"),
        ([SubTask(id=str(i), description="x") for i in range(4)], "limit is 3"),
    ],
)
def test_structure_validation_rejects_bad_plans(sub_tasks, message):
    with pytest.raises(PlanError, match=message):
        validate_plan_structure(sub_tasks, max_sub_tasks=3)


def test_execute_returns_plan_and_usage():
    provider = ScriptedProvider([plan_json(("st-1", []), ("st-2", []))])
    response = PlannerAgent(provider=provider).execute(AgentRequest(task_id="t", prompt="obj"))
    assert response.status == "success"
    assert len(response.result["plan"]["sub_tasks"]) == 2
    assert response.usage.input_tokens == 100
