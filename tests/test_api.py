"""
Tests for the FastAPI layer.

Each test gets a freshly migrated database (see tests/conftest.py) and runs
tasks inline: FastAPI's TestClient executes background tasks before a request
returns, so a task created with POST /tasks has finished by the next call.
"""


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_allows_configured_dev_origin(client):
    response = client.options(
        "/tasks",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_rejects_unlisted_origin(client):
    response = client.get("/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in response.headers


def test_create_task_returns_pending_then_completes(client):
    response = client.post("/tasks", json={"task": "Summarize multi-agent systems"})
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["input_task"] == "Summarize multi-agent systems"
    task_id = body["id"]

    # TestClient runs background tasks synchronously before returning from
    # the `with` block's request, so by the time we poll, it has completed.
    get_response = client.get(f"/tasks/{task_id}")
    assert get_response.status_code == 200
    completed = get_response.json()
    assert completed["status"] == "success"
    assert completed["result"] is not None
    assert completed["retries_used"] == 0


def test_create_task_rejects_empty_task_string(client):
    response = client.post("/tasks", json={"task": ""})
    assert response.status_code == 422


def test_get_nonexistent_task_returns_404(client):
    response = client.get("/tasks/does-not-exist")
    assert response.status_code == 404


def test_list_tasks_returns_created_tasks_most_recent_first(client):
    first = client.post("/tasks", json={"task": "first task"}).json()
    second = client.post("/tasks", json={"task": "second task"}).json()

    list_response = client.get("/tasks")
    assert list_response.status_code == 200
    ids_in_order = [t["id"] for t in list_response.json()]
    assert ids_in_order.index(second["id"]) < ids_in_order.index(first["id"])


def test_completed_task_reports_usage_totals(client):
    task_id = client.post("/tasks", json={"task": "Summarize EDF"}).json()["id"]
    body = client.get(f"/tasks/{task_id}").json()
    # Mock provider: one call each for planner, 3 research sub-tasks, validator.
    assert body["usage"]["calls"] == 5
    assert body["usage"]["cost_usd"] == 0
    assert all("usage" in step for step in body["steps"])


# --- Phase F2: validation, steps, live events, cancel, readiness ----------------

import json  # noqa: E402

import pytest  # noqa: E402


@pytest.mark.parametrize("bad", ["   ", "x" * 2001])
def test_create_task_rejects_blank_or_overlong_input(client, bad):
    assert client.post("/tasks", json={"task": bad}).status_code == 422


def test_create_task_trims_whitespace(client):
    body = client.post("/tasks", json={"task": "  Summarize EDF  "}).json()
    assert body["input_task"] == "Summarize EDF"


def test_get_task_returns_steps_in_order_with_sequence_numbers(client):
    task_id = client.post("/tasks", json={"task": "Summarize EDF"}).json()["id"]
    steps = client.get(f"/tasks/{task_id}").json()["steps"]
    assert [s["seq"] for s in steps] == list(range(1, len(steps) + 1))
    assert [s["step_name"] for s in steps] == [
        "planner",
        "research",
        "research",
        "research",
        "validator",
    ]


def test_list_tasks_omits_step_detail(client):
    client.post("/tasks", json={"task": "Summarize EDF"})
    assert client.get("/tasks").json()[0]["steps"] is None


def parse_sse(text):
    events = []
    for block in text.strip().split("\n\n"):
        fields = {}
        for line in block.splitlines():
            if line.startswith(":") or ":" not in line:
                continue
            key, _, value = line.partition(":")
            fields[key] = value.strip()
        if "event" in fields:
            events.append(fields)
    return events


def test_event_stream_replays_steps_then_reports_done(client):
    task_id = client.post("/tasks", json={"task": "Summarize EDF"}).json()["id"]
    with client.stream("GET", f"/tasks/{task_id}/events") as response:
        assert response.headers["content-type"].startswith("text/event-stream")
        events = parse_sse(response.read().decode())
    kinds = [e["event"] for e in events]
    assert kinds == ["step"] * 5 + ["status", "done"]
    assert [e["id"] for e in events[:5]] == ["1", "2", "3", "4", "5"]
    assert json.loads(events[-1]["data"])["status"] == "success"


def test_event_stream_resumes_after_last_event_id(client):
    task_id = client.post("/tasks", json={"task": "Summarize EDF"}).json()["id"]
    with client.stream(
        "GET", f"/tasks/{task_id}/events", headers={"Last-Event-ID": "3"}
    ) as response:
        events = parse_sse(response.read().decode())
    assert [e["id"] for e in events if e["event"] == "step"] == ["4", "5"]


def test_event_stream_for_unknown_task_is_404(client):
    assert client.get("/tasks/nope/events").status_code == 404


def test_cancel_unknown_task_is_404(client):
    assert client.post("/tasks/nope/cancel").status_code == 404


def test_cancel_finished_task_is_409(client):
    task_id = client.post("/tasks", json={"task": "Summarize EDF"}).json()["id"]
    response = client.post(f"/tasks/{task_id}/cancel")
    assert response.status_code == 409
    assert "already finished" in response.json()["detail"]


def test_cancel_queued_task_sets_flag(client):
    from src.shared.db import TaskRecord, session_scope

    with session_scope() as session:
        session.add(TaskRecord(id="queued-1", input_task="later", status="pending"))
    response = client.post("/tasks/queued-1/cancel")
    assert response.status_code == 202
    assert response.json()["cancel_requested"] is True


def test_ready_reports_database_and_queue(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok", "queue": "ok"}


def test_ready_returns_503_when_database_is_unreachable(client, monkeypatch):
    from src.api import main

    class BrokenEngine:
        def connect(self):
            raise OSError("connection refused")

    monkeypatch.setattr(main, "get_engine", lambda: BrokenEngine())
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["database"] == "unavailable"
