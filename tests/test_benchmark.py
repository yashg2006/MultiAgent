"""The benchmark and its report generator (run against the Mock provider)."""

import json

from scripts import benchmark, report_benchmark


def test_benchmark_runs_both_approaches_and_writes_results(tmp_path, monkeypatch):
    monkeypatch.setattr("sys.argv", ["benchmark", "--out", str(tmp_path), "--limit", "2"])
    benchmark.main()

    payload = json.loads((tmp_path / "benchmark-mock.json").read_text())
    assert payload["provider"] == "mock"
    assert payload["task_count"] == 2
    rows = payload["rows"]
    assert [r["approach"] for r in rows] == [
        "single_agent",
        "multi_agent",
        "single_agent",
        "multi_agent",
    ]
    multi = next(r for r in rows if r["approach"] == "multi_agent")
    # planner + 3 research + validator + one comparison judge call.
    assert multi["calls"] == 6
    assert multi["pipeline_status"] == "success"
    assert all(set(["seconds", "passed", "score", "cost_usd"]) <= r.keys() for r in rows)


def test_report_generator_builds_a_comparison_table(tmp_path):
    payload = {
        "generated_at": "2026-10-22T00:00:00Z",
        "provider": "anthropic",
        "model": "claude-haiku-5-5",
        "python": "3.10.0",
        "task_count": 2,
        "rows": [
            {
                "approach": "single_agent",
                "task": "t1",
                "seconds": 1.0,
                "passed": True,
                "score": 0.7,
                "calls": 2,
                "input_tokens": 100,
                "output_tokens": 50,
                "cost_usd": 0.001,
            },
            {
                "approach": "multi_agent",
                "task": "t1",
                "seconds": 3.0,
                "passed": True,
                "score": 0.9,
                "calls": 6,
                "input_tokens": 400,
                "output_tokens": 120,
                "cost_usd": 0.004,
            },
        ],
    }
    results = tmp_path / "b.json"
    results.write_text(json.dumps(payload))
    md_path = tmp_path / "b.md"
    import sys

    sys.argv = ["report", str(results), "--md", str(md_path)]
    report_benchmark.main()

    md = md_path.read_text()
    assert "Validator pass rate | 100% | 100%" in md
    assert "Average quality score | 0.70 | 0.90" in md
    assert "claude-haiku-5-5" in md
    assert "Mock" not in md  # the mock-provider note only appears for mock runs


def test_report_notes_mock_runs_are_placeholders(tmp_path):
    payload = {
        "generated_at": "x",
        "provider": "mock",
        "model": "n/a",
        "python": "3.10",
        "task_count": 1,
        "rows": [
            {
                "approach": "single_agent",
                "task": "t",
                "seconds": 0.0,
                "passed": True,
                "score": 1.0,
                "calls": 2,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
            }
        ],
    }
    assert "placeholders" in report_benchmark.to_markdown(payload)
