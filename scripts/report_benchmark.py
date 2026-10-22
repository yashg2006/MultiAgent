"""
Turn raw benchmark JSON (scripts/benchmark.py output) into the Markdown table
and the comparison chart used in the project report.

    python scripts/report_benchmark.py docs/results/benchmark-anthropic.json \
        --md docs/results/benchmark.md --chart docs/assets/benchmark.png
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path


def summarize(rows: list[dict], approach: str) -> dict:
    subset = [r for r in rows if r["approach"] == approach]
    n = len(subset)
    passed = sum(1 for r in subset if r["passed"])
    scores = [r["score"] for r in subset if isinstance(r.get("score"), (int, float))]
    return {
        "approach": approach,
        "runs": n,
        "pass_rate": passed / n if n else 0.0,
        "avg_score": statistics.mean(scores) if scores else None,
        "avg_seconds": statistics.mean(r["seconds"] for r in subset) if n else 0.0,
        "avg_calls": statistics.mean(r["calls"] for r in subset) if n else 0.0,
        "total_tokens": sum(r["input_tokens"] + r["output_tokens"] for r in subset),
        "total_cost_usd": round(sum(r["cost_usd"] for r in subset), 6),
    }


def to_markdown(payload: dict) -> str:
    rows = payload["rows"]
    single = summarize(rows, "single_agent")
    multi = summarize(rows, "multi_agent")

    def pct(x: float | None) -> str:
        return "—" if x is None else f"{x * 100:.0f}%"

    def score(x: float | None) -> str:
        return "—" if x is None else f"{x:.2f}"

    lines = [
        "# Benchmark: single-agent vs. multi-agent",
        "",
        f"- Provider: **{payload['provider']}** (model: {payload['model']})",
        f"- Tasks: {payload['task_count']}; generated {payload['generated_at']}",
        "",
        "| Metric | Single-agent baseline | Multi-agent pipeline |",
        "|--------|----------------------:|---------------------:|",
        f"| Validator pass rate | {pct(single['pass_rate'])} | {pct(multi['pass_rate'])} |",
        f"| Average quality score | {score(single['avg_score'])} | {score(multi['avg_score'])} |",
        f"| Average time per task (s) | {single['avg_seconds']:.2f} | {multi['avg_seconds']:.2f} |",
        f"| Average LLM calls per task | {single['avg_calls']:.1f} | {multi['avg_calls']:.1f} |",
        f"| Total tokens | {single['total_tokens']:,} | {multi['total_tokens']:,} |",
        (
            f"| Total estimated cost (USD) | ${single['total_cost_usd']:.4f} "
            f"| ${multi['total_cost_usd']:.4f} |"
        ),
        "",
    ]
    if payload["provider"] == "mock":
        lines.append(
            "> Note: run with the **Mock** provider, so quality and token/cost "
            "figures are placeholders (Mock returns deterministic text and reports "
            "zero tokens). Timing and call counts reflect the real control flow. "
            "Re-run with `LLM_PROVIDER=anthropic` for meaningful quality and cost."
        )
    return "\n".join(lines) + "\n"


def write_chart(payload: dict, path: Path) -> bool:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False

    single = summarize(payload["rows"], "single_agent")
    multi = summarize(payload["rows"], "multi_agent")
    metrics = ["Pass rate", "Avg score", "Avg time (s)", "Avg calls"]
    single_vals = [
        single["pass_rate"],
        single["avg_score"] or 0,
        single["avg_seconds"],
        single["avg_calls"],
    ]
    multi_vals = [
        multi["pass_rate"],
        multi["avg_score"] or 0,
        multi["avg_seconds"],
        multi["avg_calls"],
    ]

    fig, axes = plt.subplots(1, 4, figsize=(11, 3.2))
    for ax, metric, sv, mv in zip(axes, metrics, single_vals, multi_vals):
        ax.bar(["single", "multi"], [sv, mv], color=["#8aa0c6", "#3b4fd8"])
        ax.set_title(metric, fontsize=10)
        ax.tick_params(labelsize=9)
    fig.suptitle(
        f"Single-agent vs. multi-agent ({payload['provider']}, {payload['task_count']} tasks)",
        fontsize=11,
    )
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path)
    parser.add_argument("--md", type=Path, required=True)
    parser.add_argument("--chart", type=Path)
    args = parser.parse_args()

    payload = json.loads(args.results.read_text())
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.md.write_text(to_markdown(payload))
    print(f"Wrote {args.md}")
    if args.chart:
        if write_chart(payload, args.chart):
            print(f"Wrote {args.chart}")
        else:
            print("matplotlib not available; skipped chart")


if __name__ == "__main__":
    main()
