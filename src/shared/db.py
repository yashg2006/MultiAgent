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

from sqlalchemy import JSON, Column, DateTime, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tasks.db")

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class TaskRecord(Base):
    """A single orchestrator run: its input, final status, and full result."""

    __tablename__ = "tasks"

    id = Column(String, primary_key=True)
    input_task = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
    result_json = Column(JSON, nullable=True)
    error = Column(String, nullable=True)
    retries_used = Column(Integer, nullable=True)
    steps_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
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


def serialize_steps(steps: list) -> list[dict]:
    """Convert a list of RunStep (Pydantic) models to plain JSON-able dicts."""
    return json.loads(json.dumps([s.model_dump() for s in steps], default=str))
