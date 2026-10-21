"""
Persistence layer.

SQLite for local development and tests, Postgres in Docker Compose; the
choice is only `DATABASE_URL`. The schema is owned by Alembic migrations in
`migrations/` (`run_migrations()` applies them), so the models here and the
migrations must stay in sync; CI runs `alembic check` to catch drift.

Tables:
- `tasks`: one row per run (input, status, final result, cancel flag).
- `run_steps`: one row per agent step, written as each step finishes, which
  is what the live event stream reads.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Engine,
    Float,
    ForeignKey,
    String,
    UniqueConstraint,
    create_engine,
    false,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from src.shared.config import settings

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"

# Statuses after which a task never changes again.
TERMINAL_STATUSES = frozenset({"success", "partial", "error", "cancelled"})


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class TaskRecord(Base):
    """A single orchestrator run.

    status: pending (queued) -> running -> success | partial | error | cancelled
    """

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    input_task: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    result_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(String, nullable=True)
    retries_used: Mapped[int | None] = mapped_column(nullable=True)
    cancel_requested: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )


class RunStepRecord(Base):
    """One agent step of a run, in the order it finished (`seq` from 1)."""

    __tablename__ = "run_steps"
    __table_args__ = (UniqueConstraint("task_id", "seq", name="uq_run_steps_task_seq"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(
        String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    seq: Mapped[int] = mapped_column(nullable=False)
    step_name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    latency_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    sub_task_id: Mapped[str | None] = mapped_column(String, nullable=True)
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    usage: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "seq": self.seq,
            "step_name": self.step_name,
            "status": self.status,
            "latency_seconds": self.latency_seconds,
            "sub_task_id": self.sub_task_id,
            "detail": self.detail,
            "usage": self.usage,
        }


_engine: Engine | None = None
_SessionLocal = sessionmaker(autoflush=False, expire_on_commit=False)


def configure_database(url: str | None = None) -> Engine:
    """(Re)bind the session factory to `url` (default: settings.database_url)."""
    global _engine
    url = url or settings.database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    if _engine is not None:
        _engine.dispose()
    _engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
    _SessionLocal.configure(bind=_engine)
    return _engine


def get_engine() -> Engine:
    return _engine if _engine is not None else configure_database()


def get_session() -> Session:
    """A new session. Caller must close it (prefer `session_scope`)."""
    get_engine()
    return _SessionLocal()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Commit on success, roll back on error, always close."""
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def run_migrations(url: str | None = None) -> None:
    """Apply all Alembic migrations up to head (idempotent)."""
    from alembic import command
    from alembic.config import Config

    if url is None:
        # str(url) would mask the password as "***"; render it in full.
        url = get_engine().url.render_as_string(hide_password=False)
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.upgrade(config, "head")


def serialize(value: Any) -> Any:
    """Round-trip through JSON so stored values are plain JSON types."""
    return json.loads(json.dumps(value, default=str))
