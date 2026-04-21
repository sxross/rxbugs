"""Bug repository — create, get, update, close, reopen."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import bleach
from sqlalchemy import Engine, text

from db.types import ActorType, Bug, BugFilters, BugSummary, Resolution

# Tags allowed in Markdown-sourced fields (description, annotations)
_ALLOWED_TAGS = [
    "p", "em", "strong", "code", "pre", "ul", "ol", "li",
    "blockquote", "a", "br", "h1", "h2", "h3", "h4",
]
_ALLOWED_ATTRS = {"a": ["href", "title"]}


def _sanitize(text_: str | None) -> str | None:
    if text_ is None:
        return None
    return bleach.clean(text_, tags=_ALLOWED_TAGS, attributes=_ALLOWED_ATTRS)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# ID generation
# ---------------------------------------------------------------------------

def _next_id(conn) -> str:
    row = conn.execute(
        text("SELECT MAX(CAST(SUBSTR(id, 5) AS INTEGER)) FROM bugs")
    ).fetchone()
    n = (row[0] or 0) + 1
    return f"BUG-{n:04d}"


# ---------------------------------------------------------------------------
# Row → TypedDict
# ---------------------------------------------------------------------------

def _row_to_bug(row) -> Bug:
    return Bug(
        id=row[0],
        product=row[1],
        title=row[2],
        description=row[3],
        area=row[4],
        priority=row[5],
        severity=row[6],
        status=row[7],
        resolution=row[8],
        created_at=row[9],
        updated_at=row[10],
        platform=row[11],
    )


_SELECT = """
    SELECT id, product, title, description, area, priority, severity,
           status, resolution, created_at, updated_at, platform
    FROM bugs
"""
# artifact_filenames is column index 10 in the full row but we skip it in _SELECT
# since it's an internal FTS-sync field, not exposed via the API.


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create(
    engine: Engine,
    *,
    product: str,
    title: str,
    description: str | None = None,
    area: str | None = None,
    platform: str | None = None,
    priority: int | None = None,
    severity: str | None = None,
    actor: str,
    actor_type: ActorType,
) -> Bug:
    from db import audit  # avoid circular import at module level

    now = _now()
    description = _sanitize(description)

    with engine.connect() as conn:
        bug_id = _next_id(conn)
        conn.execute(
            text("""
                INSERT INTO bugs
                    (id, product, title, description, area, platform, priority,
                     severity, status, resolution, artifact_filenames,
                     created_at, updated_at)
                VALUES
                    (:id, :product, :title, :description, :area, :platform,
                     :priority, :severity, 'open', 'none', '', :now, :now)
            """),
            {
                "id": bug_id,
                "product": product,
                "title": title,
                "description": description,
                "area": area,
                "platform": platform,
                "priority": priority,
                "severity": severity,
                "now": now,
            },
        )
        audit.append(
            engine,
            bug_id=bug_id,
            actor=actor,
            actor_type=actor_type,
            field="created",
            new_value=bug_id,
            conn=conn,
        )
        conn.commit()

    # Also ensure the product exists in the products table
    _ensure_product(engine, product)
    if area:
        _ensure_area(engine, area)
    if platform:
        _ensure_platform(engine, platform)
    if severity:
        _ensure_severity(engine, severity)

    return get(engine, bug_id)  # type: ignore[return-value]


def get(engine: Engine, bug_id: str) -> Bug | None:
    with engine.connect() as conn:
        row = conn.execute(
            text(_SELECT + " WHERE id = :id"), {"id": bug_id}
        ).fetchone()
    return _row_to_bug(row) if row else None


def update(
    engine: Engine,
    bug_id: str,
    *,
    actor: str,
    actor_type: ActorType,
    **fields: Any,
) -> Bug | None:
    """Update arbitrary fields on a bug.  Only supplied fields are changed."""
    from db import audit

    bug = get(engine, bug_id)
    if bug is None:
        return None

    mutable = {"product", "title", "description", "area", "platform", "priority", "severity"}
    updates = {k: v for k, v in fields.items() if k in mutable}
    if not updates:
        return bug

    if "description" in updates:
        updates["description"] = _sanitize(updates["description"])

    now = _now()
    updates["updated_at"] = now

    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    with engine.connect() as conn:
        conn.execute(
            text(f"UPDATE bugs SET {set_clause} WHERE id = :bug_id"),
            {**updates, "bug_id": bug_id},
        )
        for field, new_val in updates.items():
            if field == "updated_at":
                continue
            audit.append(
                engine,
                bug_id=bug_id,
                actor=actor,
                actor_type=actor_type,
                field=field,
                old_value=str(bug.get(field)),  # type: ignore[arg-type]
                new_value=str(new_val) if new_val is not None else None,
                conn=conn,
            )
        conn.commit()

    if "product" in updates:
        _ensure_product(engine, updates["product"])
    if updates.get("area"):
        _ensure_area(engine, updates["area"])
    if updates.get("platform"):
        _ensure_platform(engine, updates["platform"])
    if updates.get("severity"):
        _ensure_severity(engine, updates["severity"])

    return get(engine, bug_id)


def close(
    engine: Engine,
    bug_id: str,
    *,
    resolution: Resolution,
    actor: str,
    actor_type: ActorType,
) -> Bug | None:
    """Close a bug.  Enforces status/resolution business rules."""
    from db import audit

    bug = get(engine, bug_id)
    if bug is None:
        return None
    if bug["status"] == "closed":
        raise ValueError("Bug is already closed.")
    if resolution == "none":
        raise ValueError("resolution is required when closing a bug.")

    now = _now()
    with engine.connect() as conn:
        conn.execute(
            text("""
                UPDATE bugs SET status='closed', resolution=:resolution, updated_at=:now
                WHERE id=:id
            """),
            {"resolution": resolution, "now": now, "id": bug_id},
        )
        audit.append(engine, bug_id=bug_id, actor=actor, actor_type=actor_type,
                     field="status", old_value="open", new_value="closed", conn=conn)
        audit.append(engine, bug_id=bug_id, actor=actor, actor_type=actor_type,
                     field="resolution", old_value=bug["resolution"],
                     new_value=resolution, conn=conn)
        conn.commit()
    return get(engine, bug_id)


def reopen(
    engine: Engine,
    bug_id: str,
    *,
    actor: str,
    actor_type: ActorType,
) -> Bug | None:
    """Reopen a closed bug.  Resets resolution to 'none'."""
    from db import audit

    bug = get(engine, bug_id)
    if bug is None:
        return None
    if bug["status"] == "open":
        raise ValueError("Bug is already open.")

    now = _now()
    with engine.connect() as conn:
        conn.execute(
            text("""
                UPDATE bugs SET status='open', resolution='none', updated_at=:now
                WHERE id=:id
            """),
            {"now": now, "id": bug_id},
        )
        audit.append(engine, bug_id=bug_id, actor=actor, actor_type=actor_type,
                     field="status", old_value="closed", new_value="open", conn=conn)
        audit.append(engine, bug_id=bug_id, actor=actor, actor_type=actor_type,
                     field="resolution", old_value=bug["resolution"],
                     new_value="none", conn=conn)
        conn.commit()
    return get(engine, bug_id)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ensure_product(engine: Engine, name: str) -> None:
    """Insert the product into the products table if not already present."""
    with engine.connect() as conn:
        conn.execute(
            text("INSERT OR IGNORE INTO products (name) VALUES (:name)"),
            {"name": name},
        )
        conn.commit()


def _ensure_area(engine: Engine, name: str) -> None:
    """Insert the area into the areas table if not already present."""
    with engine.connect() as conn:
        conn.execute(
            text("INSERT OR IGNORE INTO areas (name) VALUES (:name)"),
            {"name": name},
        )
        conn.commit()


def _ensure_severity(engine: Engine, name: str) -> None:
    """Insert the severity into the severities table if not already present."""
    with engine.connect() as conn:
        conn.execute(
            text("INSERT OR IGNORE INTO severities (name) VALUES (:name)"),
            {"name": name},
        )
        conn.commit()


def _ensure_platform(engine: Engine, name: str) -> None:
    """Insert the platform into the platforms table if not already present."""
    with engine.connect() as conn:
        conn.execute(
            text("INSERT OR IGNORE INTO platforms (name) VALUES (:name)"),
            {"name": name},
        )
        conn.commit()
