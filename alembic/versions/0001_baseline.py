"""baseline — existing schema applied via init.sql

Revision ID: 0001
Revises:
Create Date: 2026-06-12

This migration is intentionally empty. The database schema was bootstrapped
via migrations/init.sql before Alembic was introduced. Stamping this revision
marks the current DB as the Alembic baseline; all future schema changes go
through new Alembic revisions.
"""
from __future__ import annotations

revision: str = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
