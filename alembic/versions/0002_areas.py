"""Promote Area to an admin-managed table.

- Creates the `areas` table (mirrors `products`) and seeds the
  five legacy values so existing bugs stay valid.
- Rebuilds the `bugs` table without the `CHECK(area IN (...))`
  constraint, since Areas are now user-defined.

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-18
"""

from __future__ import annotations

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

from alembic import op


_LEGACY_AREAS = ["ui", "middleware", "backend", "database", "sync"]


def upgrade() -> None:
    # ---- areas table ----
    op.execute("""
        CREATE TABLE IF NOT EXISTS areas (
            name        TEXT PRIMARY KEY,
            description TEXT,
            archived    INTEGER NOT NULL DEFAULT 0
        )
    """)
    for name in _LEGACY_AREAS:
        op.execute(
            f"INSERT OR IGNORE INTO areas (name, description, archived) "
            f"VALUES ('{name}', NULL, 0)"
        )

    # ---- also register any Area already used on existing bugs ----
    op.execute("""
        INSERT OR IGNORE INTO areas (name, description, archived)
        SELECT DISTINCT area, NULL, 0 FROM bugs
        WHERE area IS NOT NULL AND area != ''
    """)

    # ---- rebuild bugs table to drop the CHECK constraint on area ----
    # Drop FTS triggers + virtual table first (they reference bugs).
    op.execute("DROP TRIGGER IF EXISTS bugs_fts_delete")
    op.execute("DROP TRIGGER IF EXISTS bugs_fts_update")
    op.execute("DROP TRIGGER IF EXISTS bugs_fts_insert")
    op.execute("DROP TABLE IF EXISTS bugs_fts")

    op.execute("""
        CREATE TABLE bugs_new (
            id                  TEXT PRIMARY KEY,
            product             TEXT NOT NULL,
            title               TEXT NOT NULL,
            description         TEXT,
            area                TEXT,
            priority            INTEGER CHECK(priority BETWEEN 1 AND 3),
            severity            TEXT CHECK(severity IN ('showstopper','serious','enhancement','nice_to_have')),
            status              TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','closed')),
            resolution          TEXT NOT NULL DEFAULT 'none'
                                CHECK(resolution IN ('none','fixed','no_repro','duplicate','wont_fix')),
            artifact_filenames  TEXT NOT NULL DEFAULT '',
            created_at          TEXT NOT NULL,
            updated_at          TEXT NOT NULL
        )
    """)
    op.execute("""
        INSERT INTO bugs_new
            (id, product, title, description, area, priority, severity,
             status, resolution, artifact_filenames, created_at, updated_at)
        SELECT
            id, product, title, description, area, priority, severity,
            status, resolution, artifact_filenames, created_at, updated_at
        FROM bugs
    """)
    op.execute("DROP TABLE bugs")
    op.execute("ALTER TABLE bugs_new RENAME TO bugs")

    # ---- recreate FTS5 virtual table + triggers ----
    op.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS bugs_fts USING fts5(
            id UNINDEXED,
            product,
            title,
            description,
            artifact_filenames,
            content='bugs',
            content_rowid='rowid'
        )
    """)
    op.execute("""
        CREATE TRIGGER IF NOT EXISTS bugs_fts_insert AFTER INSERT ON bugs BEGIN
            INSERT INTO bugs_fts(rowid, id, product, title, description, artifact_filenames)
            VALUES (new.rowid, new.id, new.product, new.title, new.description, new.artifact_filenames);
        END
    """)
    op.execute("""
        CREATE TRIGGER IF NOT EXISTS bugs_fts_update AFTER UPDATE ON bugs BEGIN
            UPDATE bugs_fts
            SET product=new.product, title=new.title,
                description=new.description,
                artifact_filenames=new.artifact_filenames
            WHERE id=new.id;
        END
    """)
    op.execute("""
        CREATE TRIGGER IF NOT EXISTS bugs_fts_delete AFTER DELETE ON bugs BEGIN
            DELETE FROM bugs_fts WHERE id=old.id;
        END
    """)
    # Rebuild the FTS index from the (now preserved) bugs rows.
    op.execute("INSERT INTO bugs_fts(bugs_fts) VALUES('rebuild')")


def downgrade() -> None:
    # The CHECK constraint would reject any custom areas now in use,
    # so this downgrade is intentionally minimal: it drops the areas
    # table but leaves bugs as-is (without the CHECK).
    op.execute("DROP TABLE IF EXISTS areas")
