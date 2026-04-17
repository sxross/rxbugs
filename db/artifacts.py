"""Artifact repository — file attachments for bugs."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import Engine, text

from db.types import ActorType, Artifact


def create(
    engine: Engine,
    *,
    bug_id: str,
    filename: str,
    path: str,
    mime_type: str | None = None,
    actor: str,
    actor_type: ActorType,
) -> Artifact:
    from db import audit, search as search_mod

    now = datetime.now(timezone.utc).isoformat()

    with engine.connect() as conn:
        result = conn.execute(
            text("""
                INSERT INTO artifacts (bug_id, filename, path, mime_type, uploaded_at)
                VALUES (:bug_id, :filename, :path, :mime_type, :now)
            """),
            {"bug_id": bug_id, "filename": filename, "path": path,
             "mime_type": mime_type, "now": now},
        )
        artifact_id = result.lastrowid
        conn.execute(
            text("UPDATE bugs SET updated_at=:now WHERE id=:id"),
            {"now": now, "id": bug_id},
        )
        audit.append(
            engine,
            bug_id=bug_id,
            actor=actor,
            actor_type=actor_type,
            field="artifact_added",
            new_value=filename,
            conn=conn,
        )
        conn.commit()

    # Refresh FTS artifact_filenames after commit
    _refresh_fts(engine, bug_id)

    return Artifact(
        id=artifact_id,
        bug_id=bug_id,
        filename=filename,
        path=path,
        mime_type=mime_type,
        uploaded_at=now,
    )


def get(engine: Engine, artifact_id: int) -> Artifact | None:
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT id, bug_id, filename, path, mime_type, uploaded_at
                FROM artifacts WHERE id = :id
            """),
            {"id": artifact_id},
        ).fetchone()
    if row is None:
        return None
    return Artifact(id=row[0], bug_id=row[1], filename=row[2], path=row[3],
                    mime_type=row[4], uploaded_at=row[5])


def list_for_bug(engine: Engine, bug_id: str) -> list[Artifact]:
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT id, bug_id, filename, path, mime_type, uploaded_at
                FROM artifacts WHERE bug_id = :bug_id ORDER BY uploaded_at
            """),
            {"bug_id": bug_id},
        ).fetchall()
    return [
        Artifact(id=r[0], bug_id=r[1], filename=r[2], path=r[3],
                 mime_type=r[4], uploaded_at=r[5])
        for r in rows
    ]


def _refresh_fts(engine: Engine, bug_id: str) -> None:
    """Re-sync artifact_filenames on the bugs row (triggers keep FTS in sync)."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT filename FROM artifacts WHERE bug_id = :bug_id"),
            {"bug_id": bug_id},
        ).fetchall()
        filenames = " ".join(r[0] for r in rows)
        conn.execute(
            text("UPDATE bugs SET artifact_filenames = :filenames WHERE id = :id"),
            {"filenames": filenames, "id": bug_id},
        )
        conn.commit()
