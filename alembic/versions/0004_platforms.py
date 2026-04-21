"""Add admin-managed Platform field.

- Creates the `platforms` table (mirrors `areas`/`severities`)
  and seeds common platform values.
- Adds a `platform` column to `bugs` (no CHECK).

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-19
"""

from __future__ import annotations

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

from alembic import op


_SEED_PLATFORMS = ["iOS", "Android", "Web", "macOS", "Windows", "Linux"]


def upgrade() -> None:
    # ---- platforms table ----
    op.execute("""
        CREATE TABLE IF NOT EXISTS platforms (
            name        TEXT PRIMARY KEY,
            description TEXT,
            archived    INTEGER NOT NULL DEFAULT 0
        )
    """)
    for name in _SEED_PLATFORMS:
        op.execute(
            f"INSERT OR IGNORE INTO platforms (name, description, archived) "
            f"VALUES ('{name}', NULL, 0)"
        )

    # ---- add platform column to bugs ----
    op.execute("ALTER TABLE bugs ADD COLUMN platform TEXT")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS platforms")
    # SQLite < 3.35 can't DROP COLUMN; leave the column in place.
