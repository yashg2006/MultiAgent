"""Structured logging context, log formatting, and metric recording."""

import json
import logging

from src.shared.observability import (
    LLM_CALLS,
    RUNS,
    ContextFilter,
    JsonFormatter,
    TextFormatter,
    record_run,
    record_step,
    request_id_var,
    task_id_var,
)
from src.shared.schemas import LLMUsage, RunResult, RunStep


def _record(**extra) -> logging.LogRecord:
    record = logging.makeLogRecord(
        {"name": "test", "levelno": logging.INFO, "levelname": "INFO", "msg": "hello", **extra}
    )
    ContextFilter().filter(record)
    return record


def test_context_filter_attaches_current_ids():
    token_r = request_id_var.set("req-1")
    token_t = task_id_var.set("task-9")
    try:
        record = _record()
        assert record.request_id == "req-1"
        assert record.task_id == "task-9"
    finally:
        request_id_var.reset(token_r)
        task_id_var.reset(token_t)


def test_json_formatter_emits_one_object_with_ids_and_extras():
    token = request_id_var.set("req-7")
    try:
        record = _record(status="success", duration_seconds=1.2)
        payload = json.loads(JsonFormatter().format(record))
    finally:
        request_id_var.reset(token)
    assert payload["message"] == "hello"
    assert payload["level"] == "INFO"
    assert payload["request_id"] == "req-7"
    assert payload["status"] == "success"
    assert payload["duration_seconds"] == 1.2
    assert "task_id" not in payload  # unset ids are omitted


def test_text_formatter_includes_ids_only_when_set():
    token = task_id_var.set("task-3")
    try:
        with_id = TextFormatter().format(_record())
    finally:
        task_id_var.reset(token)
    assert "task_id=task-3" in with_id
    assert "(" not in TextFormatter().format(_record())  # none set -> no id block


def _counter_value(counter, **labels) -> float:
    return counter.labels(**labels)._value.get()


def test_record_step_counts_calls_and_validator_verdicts():
    before = _counter_value(LLM_CALLS, provider="mock")
    step = RunStep(
        step_name="research",
        status="success",
        latency_seconds=0.2,
        usage=LLMUsage(calls=2, retries=1, input_tokens=100, output_tokens=20, cost_usd=0.001),
    )
    record_step(step, provider="mock")
    assert _counter_value(LLM_CALLS, provider="mock") == before + 2

    from src.shared.observability import VALIDATIONS

    passed_before = _counter_value(VALIDATIONS, verdict="pass")
    record_step(
        RunStep(step_name="validator", status="success", latency_seconds=0.1), provider="mock"
    )
    assert _counter_value(VALIDATIONS, verdict="pass") == passed_before + 1


def test_record_run_counts_by_status():
    before = _counter_value(RUNS, status="partial")
    record_run(RunResult(task_id="t", status="partial"), duration_seconds=3.0)
    assert _counter_value(RUNS, status="partial") == before + 1
