"""
Tests for the FastAPI layer (Phase D).

Uses FastAPI's TestClient (httpx) against an isolated, temporary SQLite
database so these tests never touch a developer's real tasks.db and can
run in parallel with other test runs.

NOTE ON VERIFICATION: unlike Phases B/C, these tests could not be executed
in the sandbox used to write this phase (fastapi/sqlalchemy/httpx are not
installed and the sandbox has no outbound network access to install them).
They are written to the same standard as the rest of the suite and are
expected to pass in CI or on a contributor's machine with network access;
treat the first real run's result as the actual verification record.
"""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    """A TestClient backed by a fresh, temporary SQLite file per test."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

    # Imported after DATABASE_URL is set, so the module-level engine picks it up.
    import importlib

    from src.shared import db as db_module

    importlib.reload(db_module)
    from src.api import routes as routes_module

    importlib.reload(routes_module)
    from src.api import main as main_module

    importlib.reload(main_module)

    with TestClient(main_module.app) as test_client:
        yield test_client

    os.remove(db_path)
    del os.environ["DATABASE_URL"]


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
