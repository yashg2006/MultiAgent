"""
Validator Agent implementation.
Responsible for reviewing outputs, checking safety/compliance rules, and validating responses.
"""

from __future__ import annotations

from typing import Any

from src.agents.base import Agent
from src.shared.schemas import AgentRequest, AgentResponse, ValidationResult, ValidationStatus
from src.shared.utils import setup_logger

logger = setup_logger(__name__)

_JUDGE_SYSTEM_PROMPT = (
    "You are a quality validator. Given aggregated research results, assess "
    "completeness and relevance and return a short verdict."
)


class ValidatorAgent(Agent):
    """Reviews and validates outputs for correctness, completeness, and compliance."""

    name = "validator_agent"

    def execute(self, request: AgentRequest) -> AgentResponse:
        """
        Validate aggregated results carried in `request.metadata["results"]`
        and return an AgentResponse whose `result` embeds a ValidationResult.
        """
        results = (request.metadata or {}).get("results")
        if results is None:
            return AgentResponse(
                task_id=request.task_id,
                status="error",
                error="No 'results' found in request.metadata to validate.",
            )

        validation = self.validate(results)
        response_status = "success" if validation.status == ValidationStatus.PASS else "rejected"
        return AgentResponse(
            task_id=request.task_id,
            status=response_status,
            result={"validation": validation.model_dump()},
        )

    def validate(self, result_data: dict[str, Any]) -> ValidationResult:
        """
        Validate aggregated agent outputs against schema and quality constraints.

        Rule checks (deterministic, no LLM required):
          - result_data must be a non-empty dict.
          - every value must be present and non-empty (no sub-task silently
            returned nothing).
          - no value may itself carry an "error" key, which would indicate an
            upstream agent failure that slipped through.

        A lightweight LLM-judge pass then supplies a qualitative score; this
        is advisory only with the Mock provider (it never flips a pass/fail
        rule-check verdict) and becomes meaningful once a real provider is
        configured.
        """
        reasons: list[str] = []

        if not result_data:
            return ValidationResult(
                status=ValidationStatus.FAIL,
                score=0.0,
                reasons=["result_data is empty"],
            )

        for key, value in result_data.items():
            if value in (None, "", [], {}):
                reasons.append(f"'{key}' is empty")
            elif isinstance(value, dict) and value.get("error"):
                reasons.append(f"'{key}' contains an error: {value['error']}")

        status = ValidationStatus.FAIL if reasons else ValidationStatus.PASS

        try:
            judge_output = self.provider.complete(str(result_data), system=_JUDGE_SYSTEM_PROMPT)
            score = 1.0 if status == ValidationStatus.PASS else 0.0
            if judge_output:
                reasons.append(f"judge: {judge_output[:80]}")
        except Exception:  # noqa: BLE001 - the judge pass is advisory, never fatal
            logger.exception("LLM-judge pass failed; continuing with rule-check verdict only")
            score = 1.0 if status == ValidationStatus.PASS else 0.0

        return ValidationResult(status=status, score=score, reasons=reasons)
