"""Audit log repository — append-only.

Every mutation to a bug is recorded here.  The log is never exposed
via the public API; inspection requires direct database access.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Engine, text

from db.types import ActorType


def append(
    engine: Engine,
    *,
    bug_id: str,
    actor: str,
    actor_type: ActorType,
    field: str,
    old_value: str | None = None,
    new_value: str | None = None,
    conn=None,
) -> None:
    """Write one audit entry.

    If *conn* is supplied the insert runs within that connection
    (allowing the caller to keep everything in one transaction).
    Otherwise a new connection is opened.
    """
    now = datetime.now(timezone.utc).isoformat()
    sql = text("""
        INSERT INTO audit_log (bug_id, actor, actor_type, field, old_value, new_value, changed_at)
        VALUES (:bug_id, :actor, :actor_type, :field, :old_value, :new_value, :changed_at)
    """)
    params = {
        "bug_id": bug_id,
        "actor": actor,
        "actor_type": actor_type,
        "field": field,
        "old_value": old_value,
        "new_value": new_value,
        "changed_at": now,
    }

    if conn is not None:
        conn.execute(sql, params)
    else:
        with engine.connect() as c:
            c.execute(sql, params)
            c.commit()
