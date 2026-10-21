"""
Persistence layer for the API (Phase D).

Uses SQLite via SQLAlchemy — zero setup, real persistence, and small enough
to be a sensible choice for a course project. The schema is deliberately
simple: one row per orchestrator run, holding the full RunResult as JSON
alongside queryable status/timestamps.

Upgrading to Postgres later (if ever wanted) only requires changing
`DATABASE_URL`; no application code depends on SQLite specifically.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tasks.db")

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class TaskRecord(Base):
    """A single orchestrator run: its input, final status, and full result."""

    __tablename__ = "tasks"

    # SQLAlchemy 2.0 typed declarations: `Mapped[...]` makes instance attributes
    # type as plain Python values (str, int, ...) rather than `Column[...]`, which
    # is what lets mypy check assignments like `record.status = "success"`.
    id: Mapped[str] = mapped_column(String, primary_key=True)
    input_task: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    result_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(String, nullable=True)
    retries_used: Mapped[int | None] = mapped_column(nullable=True)
    steps_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


def init_db() -> None:
    """Create all tables if they don't already exist. Safe to call repeatedly."""
    Base.metadata.create_all(bind=engine)


def get_session() -> Session:
    """Return a new SQLAlchemy session. Caller is responsible for closing it."""
    return SessionLocal()


def serialize_steps(steps: list[Any]) -> list[dict[str, Any]]:
    """Convert a list of RunStep (Pydantic) models to plain JSON-able dicts."""
    serialized: list[dict[str, Any]] = json.loads(
        json.dumps([s.model_dump() for s in steps], default=str)
    )
    return serialized
