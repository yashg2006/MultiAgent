"""Accounts: users table and task ownership.

Revision ID: 0002_users
Revises: 0001_initial
Create Date: 2026-10-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_users"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    with op.batch_alter_table("tasks") as batch:
        batch.add_column(sa.Column("user_id", sa.String(), nullable=True))
        batch.create_index("ix_tasks_user_id", ["user_id"], unique=False)
        batch.create_foreign_key(
            "fk_tasks_user_id_users", "users", ["user_id"], ["id"], ondelete="CASCADE"
        )


def downgrade() -> None:
    with op.batch_alter_table("tasks") as batch:
        batch.drop_constraint("fk_tasks_user_id_users", type_="foreignkey")
        batch.drop_index("ix_tasks_user_id")
        batch.drop_column("user_id")
    op.drop_table("users")
