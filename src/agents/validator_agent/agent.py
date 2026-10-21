"""
Validator Agent implementation.
Responsible for reviewing outputs, checking safety/compliance rules, and validating responses.
"""

from __future__ import annotations

from typing import Any

from src.agents.base import Agent
from src.shared.config import settings
from src.shared.llm_provider import extract_json_object
from src.shared.schemas import (
    AgentRequest,
    AgentResponse,
    LLMUsage,
    ValidationResult,
    ValidationStatus,
)
from src.shared.utils import setup_logger

logger = setup_logger(__name__)

_JUDGE_SYSTEM_PROMPT = (
    "You review research results for a stated objective. Score how well the findings, "
    "taken together, answer the objective, from 0.0 to 1.0, using this rubric:\n"
    "- relevance: findings address the objective, not something else\n"
    "- completeness: every part of the objective is covered\n"
    "- consistency: findings do not contradict each other\n"
    "- specificity: concrete, checkable statements rather than filler\n"
    "Respond with ONLY a JSON object: "
    '{"score": <number 0.0-1.0>, "reasons": ["<short reason>", ...]}'
)

_MAX_CHARS_PER_FINDING = 1500


class ValidatorAgent(Agent):
    """Reviews aggregated results: deterministic rule checks, then an LLM judge."""

    name = "validator_agent"

    @property
    def threshold(self) -> float:
        return float(self.config.get("judge_threshold", settings.judge_threshold))

    def execute(self, request: AgentRequest) -> AgentResponse:
        """
        Validate aggregated results carried in `request.metadata["results"]`
        (and the original objective in `request.metadata["objective"]`).
        """
        metadata = request.metadata or {}
        results = metadata.get("results")
        if results is None:
            return AgentResponse(
                task_id=request.task_id,
                status="error",
                error="No 'results' found in request.metadata to validate.",
            )

        validation, usage = self.validate_with_usage(results, metadata.get("objective"))
        response_status = "success" if validation.status == ValidationStatus.PASS else "rejected"
        return AgentResponse(
            task_id=request.task_id,
            status=response_status,
            result={"validation": validation.model_dump()},
            usage=usage,
        )

    def validate(
        self, result_data: dict[str, Any], objective: str | None = None
    ) -> ValidationResult:
        """Validate results (usage discarded); see `validate_with_usage`."""
        validation, _ = self.validate_with_usage(result_data, objective)
        return validation

    def validate_with_usage(
        self, result_data: dict[str, Any], objective: str | None = None
    ) -> tuple[ValidationResult, LLMUsage]:
        """
        1. Rule checks (deterministic, no LLM): results must be non-empty, every
           sub-task must have content, and none may carry an upstream "error".
           Any failure here rejects immediately; the judge isn't consulted.
        2. LLM judge: scores the findings 0-1 against a rubric. The result passes
           only if the score reaches `judge_threshold`. If the judge can't be
           reached or returns unusable output, the rule-check verdict stands and
           the reason says so — a judge outage must not block every run.
        """
        if not result_data:
            return (
                ValidationResult(status=ValidationStatus.FAIL, score=0.0, reasons=["No results."]),
                LLMUsage(),
            )

        reasons: list[str] = []
        for key, value in result_data.items():
            if value in (None, "", [], {}):
                reasons.append(f"'{key}' is empty")
            elif isinstance(value, dict) and value.get("error"):
                reasons.append(f"'{key}' contains an error: {value['error']}")
            elif isinstance(value, dict) and not str(value.get("findings", "x")).strip():
                reasons.append(f"'{key}' has no findings")
        if reasons:
            return ValidationResult(status=ValidationStatus.FAIL, score=0.0, reasons=reasons), (
                LLMUsage()
            )

        try:
            response, usage = self.call_llm(
                self._judge_prompt(result_data, objective),
                system=_JUDGE_SYSTEM_PROMPT,
                kind="judge",
            )
        except Exception as exc:  # noqa: BLE001 - judge outage must not block runs
            logger.exception("LLM judge failed; using rule-check verdict only")
            return (
                ValidationResult(
                    status=ValidationStatus.PASS,
                    score=None,
                    reasons=[f"Rule checks passed; quality check unavailable ({exc})."],
                ),
                LLMUsage(),
            )

        verdict = extract_json_object(response.text) or {}
        score = verdict.get("score")
        judge_reasons = [str(r) for r in verdict.get("reasons", []) if str(r).strip()]
        if not isinstance(score, (int, float)) or not 0.0 <= float(score) <= 1.0:
            return (
                ValidationResult(
                    status=ValidationStatus.PASS,
                    score=None,
                    reasons=["Rule checks passed; quality check returned no usable score."],
                ),
                usage,
            )

        score = float(score)
        passed = score >= self.threshold
        summary = (
            f"Quality score {score:.2f} meets the {self.threshold:.2f} threshold."
            if passed
            else f"Quality score {score:.2f} is below the {self.threshold:.2f} threshold."
        )
        return (
            ValidationResult(
                status=ValidationStatus.PASS if passed else ValidationStatus.FAIL,
                score=score,
                reasons=[summary, *judge_reasons],
            ),
            usage,
        )

    @staticmethod
    def _judge_prompt(result_data: dict[str, Any], objective: str | None) -> str:
        lines = [f"Objective: {objective or '(not provided)'}", "", "Findings:"]
        for key, value in result_data.items():
            if isinstance(value, dict):
                question = value.get("query", "")
                findings = str(value.get("findings", ""))[:_MAX_CHARS_PER_FINDING]
                lines.append(f"[{key}] {question}\n{findings}")
            else:
                lines.append(f"[{key}] {str(value)[:_MAX_CHARS_PER_FINDING]}")
        return "\n\n".join(lines)
