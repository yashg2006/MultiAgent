"""Shared fixtures.

Database tests run the real Alembic migrations against a fresh SQLite file per
test, or against Postgres when TEST_DATABASE_URL is set (CI does both), so the
migrations themselves are exercised on every run.
"""

from __future__ import annotations

import os

import pytest

from src.shared.config import settings
from src.shared.db import configure_database, run_migrations

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


def _downgrade_all(url: str) -> None:
    from alembic import command
    from alembic.config import Config

    from src.shared.db import MIGRATIONS_DIR

    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    config.set_main_option("sqlalchemy.url", url)
    command.downgrade(config, "base")


@pytest.fixture()
def database_url(tmp_path, monkeypatch):
    """A migrated, empty database bound as the app's database."""
    url = TEST_DATABASE_URL or f"sqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setattr(settings, "database_url", url)
    configure_database(url)
    if TEST_DATABASE_URL:
        _downgrade_all(url)  # start clean even if a previous run died
    run_migrations(url)
    yield url
    if TEST_DATABASE_URL:
        _downgrade_all(url)


@pytest.fixture()
def client(database_url, monkeypatch):
    """A TestClient running tasks inline, against the per-test database."""
    from fastapi.testclient import TestClient

    from src.api.main import app

    monkeypatch.setattr(settings, "queue_backend", "inline")
    monkeypatch.setattr(settings, "sse_poll_seconds", 0.01)
    with TestClient(app) as test_client:
        yield test_client
