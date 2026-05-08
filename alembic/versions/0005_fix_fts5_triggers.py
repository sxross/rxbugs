"""Fix FTS5 triggers to use the delete-and-insert pattern.

The external-content FTS5 table (``bugs_fts``) requires the
SQLite-recommended pattern of issuing a ``DELETE`` (via the special
``'delete'`` command) followed by a fresh ``INSERT`` when a row is
updated, and a ``DELETE`` (via ``'delete'``) when a row is removed.

Previous migrations used ``UPDATE bugs_fts SET …`` and
``DELETE FROM bugs_fts WHERE …`` which are incorrect for external-content
FTS5 tables and can corrupt the index.

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-07
"""

from __future__ import annotations

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

from alembic import op


def upgrade() -> None:
    # Drop the broken triggers.
    op.execute("DROP TRIGGER IF EXISTS bugs_fts_update")
    op.execute("DROP TRIGGER IF EXISTS bugs_fts_delete")

    # Recreate with the correct delete-and-insert pattern.
    op.execute("""
        CREATE TRIGGER bugs_fts_update AFTER UPDATE ON bugs BEGIN
            INSERT INTO bugs_fts(bugs_fts, rowid, id, product, title,
                                 description, artifact_filenames)
            VALUES ('delete', old.rowid, old.id, old.product, old.title,
                    old.description, old.artifact_filenames);
            INSERT INTO bugs_fts(rowid, id, product, title,
                                 description, artifact_filenames)
            VALUES (new.rowid, new.id, new.product, new.title,
                    new.description, new.artifact_filenames);
        END
    """)
    op.execute("""
        CREATE TRIGGER bugs_fts_delete AFTER DELETE ON bugs BEGIN
            INSERT INTO bugs_fts(bugs_fts, rowid, id, product, title,
                                 description, artifact_filenames)
            VALUES ('delete', old.rowid, old.id, old.product, old.title,
                    old.description, old.artifact_filenames);
        END
    """)

    # Rebuild the FTS index to fix any prior corruption.
    op.execute("INSERT INTO bugs_fts(bugs_fts) VALUES('rebuild')")


def downgrade() -> None:
    # Restore the old (broken) triggers — kept for reversibility only.
    op.execute("DROP TRIGGER IF EXISTS bugs_fts_update")
    op.execute("DROP TRIGGER IF EXISTS bugs_fts_delete")

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
    op.execute("INSERT INTO bugs_fts(bugs_fts) VALUES('rebuild')")
