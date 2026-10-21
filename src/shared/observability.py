"""
Logging context and Prometheus metrics.

Logging: every record carries the current `request_id` and `task_id` (from
context variables set by the API middleware and the worker), so one run can
be followed across the API and worker logs. `LOG_FORMAT=json` emits one JSON
object per line for log collectors; `text` (default) is for humans.

Metrics: module-level Prometheus collectors. The API serves them at
`/metrics`; each worker serves its own on `WORKER_METRICS_PORT`. Counters are
per process; Prometheus sums them across processes.
"""

from __future__ import annotations

import json
import logging
from contextvars import ContextVar
from datetime import datetime, timezone

from prometheus_client import Counter, Histogram

from src.shared.schemas import RunResult, RunStep

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
task_id_var: ContextVar[str | None] = ContextVar("task_id", default=None)

_STANDARD_ATTRS = set(vars(logging.makeLogRecord({}))) | {"message", "asctime"}


class ContextFilter(logging.Filter):
    """Attach the current request and task ids to every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        record.task_id = task_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    """One JSON object per line: ts, level, logger, message, ids, extras."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("request_id", "task_id"):
            value = getattr(record, key, None)
            if value:
                payload[key] = value
        for key, value in vars(record).items():
            if (
                key not in _STANDARD_ATTRS
                and key not in payload
                and key
                not in (
                    "request_id",
                    "task_id",
                )
            ):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class TextFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__("[%(asctime)s] %(levelname)s [%(name)s]%(ids)s: %(message)s")

    def format(self, record: logging.LogRecord) -> str:
        ids = [
            f"{key}={getattr(record, key)}"
            for key in ("request_id", "task_id")
            if getattr(record, key, None)
        ]
        record.ids = f" ({' '.join(ids)})" if ids else ""
        return super().format(record)


def make_formatter(log_format: str) -> logging.Formatter:
    return JsonFormatter() if log_format.strip().lower() == "json" else TextFormatter()


# --- Metrics ----------------------------------------------------------------

HTTP_REQUESTS = Counter(
    "http_requests_total", "HTTP requests handled", ["method", "route", "status"]
)
HTTP_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency (streaming responses: time to first byte)",
    ["method", "route"],
)
RUNS = Counter("pipeline_runs_total", "Finished pipeline runs", ["status"])
RUN_DURATION = Histogram(
    "pipeline_run_duration_seconds",
    "Wall-clock time of a pipeline run",
    buckets=(0.1, 0.5, 1, 2.5, 5, 10, 20, 40, 60, 120, 300, 600),
)
STEP_DURATION = Histogram(
    "agent_step_duration_seconds",
    "Time per agent step",
    ["agent"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10, 20, 40, 60),
)
LLM_CALLS = Counter("llm_calls_total", "Model calls, including retries", ["provider"])
LLM_RETRIES = Counter("llm_retries_total", "Model calls that were retries", ["provider"])
LLM_TOKENS = Counter("llm_tokens_total", "Model tokens", ["provider", "direction"])
LLM_COST = Counter("llm_cost_usd_total", "Estimated model cost in USD", ["provider"])
VALIDATIONS = Counter(
    "validator_verdicts_total", "Validator decisions on aggregated results", ["verdict"]
)


def record_step(step: RunStep, provider: str) -> None:
    """Update metrics for one finished agent step."""
    STEP_DURATION.labels(agent=step.step_name).observe(step.latency_seconds)
    usage = step.usage
    if usage.calls:
        LLM_CALLS.labels(provider=provider).inc(usage.calls)
    if usage.retries:
        LLM_RETRIES.labels(provider=provider).inc(usage.retries)
    if usage.input_tokens:
        LLM_TOKENS.labels(provider=provider, direction="input").inc(usage.input_tokens)
    if usage.output_tokens:
        LLM_TOKENS.labels(provider=provider, direction="output").inc(usage.output_tokens)
    if usage.cost_usd:
        LLM_COST.labels(provider=provider).inc(usage.cost_usd)
    if step.step_name == "validator" and step.status in ("success", "rejected"):
        VALIDATIONS.labels(verdict="pass" if step.status == "success" else "fail").inc()


def record_run(result: RunResult, duration_seconds: float) -> None:
    """Update metrics for one finished run."""
    RUNS.labels(status=result.status).inc()
    RUN_DURATION.observe(duration_seconds)
