"""Validator Agent: rule checks plus the LLM-judge score threshold."""

import json

from src.agents.validator_agent.agent import ValidatorAgent
from src.shared.schemas import AgentRequest, ValidationStatus
from tests.fakes import ScriptedProvider

GOOD = {"st-1": {"query": "What is EDF?", "findings": "Earliest deadline first ..."}}


def judge(score, reasons=("fine",)):
    return json.dumps({"score": score, "reasons": list(reasons)})


def test_passes_when_judge_score_meets_threshold():
    agent = ValidatorAgent(provider=ScriptedProvider([judge(0.8)]))
    result, usage = agent.validate_with_usage(GOOD, "Explain EDF")
    assert result.status == ValidationStatus.PASS
    assert result.score == 0.8
    assert "meets" in result.reasons[0]
    assert usage.calls == 1


def test_fails_when_judge_score_is_below_threshold_and_keeps_reasons():
    agent = ValidatorAgent(provider=ScriptedProvider([judge(0.3, ["misses RMS"])]))
    result = agent.validate(GOOD, "Compare EDF and RMS")
    assert result.status == ValidationStatus.FAIL
    assert "below" in result.reasons[0]
    assert "misses RMS" in result.reasons


def test_threshold_is_configurable():
    agent = ValidatorAgent(provider=ScriptedProvider([judge(0.5)]), config={"judge_threshold": 0.4})
    assert agent.validate(GOOD).status == ValidationStatus.PASS


def test_judge_prompt_includes_objective_and_findings():
    provider = ScriptedProvider([judge(0.9)])
    ValidatorAgent(provider=provider).validate(GOOD, "Explain EDF")
    prompt = provider.calls[0]["prompt"]
    assert "Objective: Explain EDF" in prompt
    assert "Earliest deadline first" in prompt
    assert provider.calls[0]["kind"] == "judge"


def test_rule_failures_skip_the_judge_entirely():
    provider = ScriptedProvider([])  # any call would raise
    result = ValidatorAgent(provider=provider).validate({"st-1": {"error": "boom"}})
    assert result.status == ValidationStatus.FAIL
    assert provider.calls == []


def test_blank_findings_fail_rule_checks():
    result = ValidatorAgent(provider=ScriptedProvider([])).validate({"st-1": {"findings": "  "}})
    assert result.status == ValidationStatus.FAIL


def test_unusable_judge_output_falls_back_to_rule_verdict():
    result = ValidatorAgent(provider=ScriptedProvider(["I think it's good"])).validate(GOOD)
    assert result.status == ValidationStatus.PASS
    assert result.score is None
    assert "no usable score" in result.reasons[0]


def test_out_of_range_score_is_treated_as_unusable():
    result = ValidatorAgent(provider=ScriptedProvider([judge(7)])).validate(GOOD)
    assert result.score is None


def test_judge_outage_does_not_block_the_run():
    result = ValidatorAgent(provider=ScriptedProvider([ValueError("down")])).validate(GOOD)
    assert result.status == ValidationStatus.PASS
    assert "unavailable" in result.reasons[0]


def test_execute_reports_usage_and_rejection_status():
    agent = ValidatorAgent(provider=ScriptedProvider([judge(0.1)]))
    response = agent.execute(
        AgentRequest(task_id="t", prompt="v", metadata={"results": GOOD, "objective": "o"})
    )
    assert response.status == "rejected"
    assert response.usage.calls == 1
