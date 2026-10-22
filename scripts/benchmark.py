"""
Benchmark: single-agent baseline vs. the multi-agent pipeline.

For each task it runs:
  (a) a single-agent baseline - one LLM call that answers the whole task, then
      the same Validator judges the answer; and
  (b) the full pipeline (Orchestrator: plan -> research -> validate -> retry).

Both are judged by the same Validator, so quality is comparable. It records,
per task and per approach: wall-clock time, validator pass/score, LLM calls,
tokens, and estimated cost. Raw results are written to docs/results/ as JSON;
`scripts/report_benchmark.py` turns them into the tables/charts in the report.

Run offline with the Mock provider (free, structural check) or against a real
model by setting LLM_PROVIDER=anthropic and ANTHROPIC_API_KEY.

    python scripts/benchmark.py --out docs/results
"""

from __future__ import annotations

import argparse
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

from src.agents.base import Agent
from src.agents.validator_agent.agent import ValidatorAgent
from src.orchestrator.main import Orchestrator
from src.shared.config import settings
from src.shared.schemas import AgentRequest, LLMUsage

# 15 varied tasks: factual, comparative, planning, explanatory, across domains.
TASKS: list[str] = [
    "Compare rate-monotonic and earliest-deadline-first scheduling and say when to prefer each.",
    "Explain how TCP congestion control (slow start and congestion avoidance) works.",
    "Outline the main causes of the 2008 financial crisis.",
    "Describe how a solid-state drive differs from a hard disk drive in operation and trade-offs.",
    "Summarize the water cycle and the role of evaporation, condensation, and precipitation.",
    "Explain the CAP theorem and what it means for distributed databases.",
    "Compare supervised and unsupervised machine learning with examples of each.",
    "Describe how vaccines train the immune system to recognize a pathogen.",
    "Explain how public-key cryptography enables secure key exchange.",
    "Outline the key steps of photosynthesis and what each produces.",
    "Compare the REST and GraphQL approaches to building web APIs.",
    "Explain how a hash table achieves average constant-time lookups and when it degrades.",
    "Describe the causes and effects of ocean acidification.",
    "Explain the difference between processes and threads in an operating system.",
    "Summarize how a blockchain reaches consensus using proof of work.",
]

_BASELINE_SYSTEM = (
    "You are a knowledgeable assistant. Answer the user's task directly, "
    "thoroughly, and factually in under 300 words."
)


def _judge(validator: ValidatorAgent, task: str, text: str) -> tuple[bool, float | None, LLMUsage]:
    """Score one answer with the Validator, as a single aggregated finding."""
    results = {"answer": {"query": task, "findings": text}}
    validation, usage = validator.validate_with_usage(results, objective=task)
    return validation.status.value == "pass", validation.score, usage


def run_baseline(task: str, agent: Agent, validator: ValidatorAgent) -> dict:
    start = time.perf_counter()
    response, usage = agent.call_llm(task, system=_BASELINE_SYSTEM)
    passed, score, judge_usage = _judge(validator, task, response.text)
    total = usage + judge_usage
    return {
        "approach": "single_agent",
        "task": task,
        "seconds": round(time.perf_counter() - start, 3),
        "passed": passed,
        "score": score,
        "calls": total.calls,
        "input_tokens": total.input_tokens,
        "output_tokens": total.output_tokens,
        "cost_usd": total.cost_usd,
    }


def _combine_findings(result_dict: dict | None) -> str:
    """One text blob from a pipeline run's per-sub-task findings, for judging."""
    if not result_dict:
        return ""
    parts = []
    for sub in result_dict.values():
        if isinstance(sub, dict) and sub.get("findings"):
            parts.append(str(sub["findings"]))
    return "\n\n".join(parts)


def run_pipeline(task: str, orchestrator: Orchestrator, validator: ValidatorAgent) -> dict:
    start = time.perf_counter()
    result = orchestrator.run(task)
    seconds = round(time.perf_counter() - start, 3)
    # Re-judge the final answer with the same Validator used for the baseline,
    # so the quality score is directly comparable. Both approaches pay one judge
    # call, so the comparison stays symmetric.
    passed, score, judge_usage = _judge(validator, task, _combine_findings(result.result))
    total = result.usage + judge_usage
    return {
        "approach": "multi_agent",
        "task": task,
        "seconds": seconds,
        "passed": passed,
        "score": score,
        "pipeline_status": result.status,
        "retries_used": result.retries_used,
        "calls": total.calls,
        "input_tokens": total.input_tokens,
        "output_tokens": total.output_tokens,
        "cost_usd": total.cost_usd,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("docs/results"))
    parser.add_argument("--limit", type=int, default=len(TASKS), help="run only the first N tasks")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    # A bare agent only to reuse call_llm for the baseline; it runs no pipeline.
    class _Baseline(Agent):
        name = "baseline"

        def execute(self, request: AgentRequest):  # pragma: no cover - unused
            raise NotImplementedError

    baseline_agent = _Baseline()
    validator = ValidatorAgent()
    orchestrator = Orchestrator()

    rows: list[dict] = []
    tasks = TASKS[: args.limit]
    for i, task in enumerate(tasks, 1):
        print(f"[{i}/{len(tasks)}] {task[:60]}...", flush=True)
        rows.append(run_baseline(task, baseline_agent, validator))
        rows.append(run_pipeline(task, orchestrator, validator))

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": settings.llm_provider,
        "model": settings.anthropic_model if settings.llm_provider == "anthropic" else "n/a",
        "python": platform.python_version(),
        "task_count": len(tasks),
        "rows": rows,
    }
    out_file = args.out / f"benchmark-{settings.llm_provider}.json"
    out_file.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {out_file}")


if __name__ == "__main__":
    main()
