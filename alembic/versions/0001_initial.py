"""Initial schema — all tables, FTS5 index, and triggers.

Revision ID: 0001
Revises:
Create Date: 2026-04-17
"""

from __future__ import annotations

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

from alembic import op


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS bugs (
            id                  TEXT PRIMARY KEY,
            product             TEXT NOT NULL,
            title               TEXT NOT NULL,
            description         TEXT,
            area                TEXT CHECK(area IN ('ui','middleware','backend','database','sync')),
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
        CREATE TABLE IF NOT EXISTS bug_relations (
            bug_id     TEXT NOT NULL REFERENCES bugs(id),
            related_id TEXT NOT NULL REFERENCES bugs(id),
            PRIMARY KEY (bug_id, related_id)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS annotations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            bug_id      TEXT NOT NULL REFERENCES bugs(id),
            author      TEXT NOT NULL,
            author_type TEXT NOT NULL CHECK(author_type IN ('human','agent')),
            body        TEXT NOT NULL,
            created_at  TEXT NOT NULL
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS artifacts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            bug_id      TEXT NOT NULL REFERENCES bugs(id),
            filename    TEXT NOT NULL,
            path        TEXT NOT NULL,
            mime_type   TEXT,
            uploaded_at TEXT NOT NULL
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS products (
            name        TEXT PRIMARY KEY,
            description TEXT,
            archived    INTEGER NOT NULL DEFAULT 0
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            key         TEXT PRIMARY KEY,
            name        TEXT NOT NULL UNIQUE,
            description TEXT,
            created_at  TEXT NOT NULL,
            active      INTEGER NOT NULL DEFAULT 1,
            rate_limit  INTEGER NOT NULL DEFAULT 60
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            bug_id      TEXT NOT NULL REFERENCES bugs(id),
            actor       TEXT NOT NULL,
            actor_type  TEXT NOT NULL CHECK(actor_type IN ('human','agent')),
            field       TEXT NOT NULL,
            old_value   TEXT,
            new_value   TEXT,
            changed_at  TEXT NOT NULL
        )
    """)

    # FTS5 virtual table
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

    # Keep FTS in sync with bugs table via triggers (safety net;
    # the repository layer also calls _refresh_fts() explicitly).
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


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS bugs_fts_delete")
    op.execute("DROP TRIGGER IF EXISTS bugs_fts_update")
    op.execute("DROP TRIGGER IF EXISTS bugs_fts_insert")
    op.execute("DROP TABLE IF EXISTS bugs_fts")
    op.execute("DROP TABLE IF EXISTS audit_log")
    op.execute("DROP TABLE IF EXISTS agents")
    op.execute("DROP TABLE IF EXISTS products")
    op.execute("DROP TABLE IF EXISTS artifacts")
    op.execute("DROP TABLE IF EXISTS annotations")
    op.execute("DROP TABLE IF EXISTS bug_relations")
    op.execute("DROP TABLE IF EXISTS bugs")
