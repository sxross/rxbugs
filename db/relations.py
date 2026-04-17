"""Bug relations repository — linking bugs together."""

from __future__ import annotations

from sqlalchemy import Engine, text

from db.types import ActorType


def link(
    engine: Engine,
    bug_id: str,
    related_id: str,
    *,
    actor: str,
    actor_type: ActorType,
) -> None:
    """Link two bugs.  Inserts both directions so queries are simpler."""
    from db import audit

    if bug_id == related_id:
        raise ValueError("A bug cannot be related to itself.")

    a, b = sorted([bug_id, related_id])
    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT OR IGNORE INTO bug_relations (bug_id, related_id)
                VALUES (:a, :b)
            """),
            {"a": a, "b": b},
        )
        audit.append(
            engine,
            bug_id=bug_id,
            actor=actor,
            actor_type=actor_type,
            field="relation_added",
            new_value=related_id,
            conn=conn,
        )
        conn.commit()


def unlink(
    engine: Engine,
    bug_id: str,
    related_id: str,
    *,
    actor: str,
    actor_type: ActorType,
) -> bool:
    """Remove a relation.  Returns True if the relation existed."""
    from db import audit

    a, b = sorted([bug_id, related_id])
    with engine.connect() as conn:
        result = conn.execute(
            text("DELETE FROM bug_relations WHERE bug_id=:a AND related_id=:b"),
            {"a": a, "b": b},
        )
        if result.rowcount:
            audit.append(
                engine,
                bug_id=bug_id,
                actor=actor,
                actor_type=actor_type,
                field="relation_removed",
                old_value=related_id,
                conn=conn,
            )
        conn.commit()
    return result.rowcount > 0


def list_for_bug(engine: Engine, bug_id: str) -> list[str]:
    """Return IDs of all bugs related to *bug_id* (both directions)."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT related_id FROM bug_relations WHERE bug_id = :id
                UNION
                SELECT bug_id FROM bug_relations WHERE related_id = :id
            """),
            {"id": bug_id},
        ).fetchall()
    return [r[0] for r in rows]
