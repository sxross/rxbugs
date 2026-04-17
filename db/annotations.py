"""Annotation repository — append-only comment log."""

from __future__ import annotations

from datetime import datetime, timezone

import bleach
from sqlalchemy import Engine, text

from db.types import ActorType, Annotation

_ALLOWED_TAGS = [
    "p", "em", "strong", "code", "pre", "ul", "ol", "li",
    "blockquote", "a", "br", "h1", "h2", "h3", "h4",
]
_ALLOWED_ATTRS = {"a": ["href", "title"]}


def _sanitize(body: str) -> str:
    return bleach.clean(body, tags=_ALLOWED_TAGS, attributes=_ALLOWED_ATTRS)


def create(
    engine: Engine,
    *,
    bug_id: str,
    author: str,
    author_type: ActorType,
    body: str,
) -> Annotation:
    from db import audit

    body = _sanitize(body)
    now = datetime.now(timezone.utc).isoformat()

    with engine.connect() as conn:
        result = conn.execute(
            text("""
                INSERT INTO annotations (bug_id, author, author_type, body, created_at)
                VALUES (:bug_id, :author, :author_type, :body, :now)
            """),
            {"bug_id": bug_id, "author": author, "author_type": author_type,
             "body": body, "now": now},
        )
        annotation_id = result.lastrowid
        # Update bug's updated_at
        conn.execute(
            text("UPDATE bugs SET updated_at=:now WHERE id=:id"),
            {"now": now, "id": bug_id},
        )
        audit.append(
            engine,
            bug_id=bug_id,
            actor=author,
            actor_type=author_type,
            field="annotation_added",
            new_value=str(annotation_id),
            conn=conn,
        )
        conn.commit()

    return Annotation(
        id=annotation_id,
        bug_id=bug_id,
        author=author,
        author_type=author_type,
        body=body,
        created_at=now,
    )


def list_for_bug(engine: Engine, bug_id: str) -> list[Annotation]:
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT id, bug_id, author, author_type, body, created_at
                FROM annotations
                WHERE bug_id = :bug_id
                ORDER BY created_at
            """),
            {"bug_id": bug_id},
        ).fetchall()
    return [
        Annotation(id=r[0], bug_id=r[1], author=r[2], author_type=r[3],
                   body=r[4], created_at=r[5])
        for r in rows
    ]
