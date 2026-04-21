"""Severities repository — controlled severity list management.

Mirrors ``db/areas.py``. Severities are user-defined classification
labels (e.g. "showstopper", "enhancement") attached to bugs.
"""

from __future__ import annotations

from sqlalchemy import Engine, text

from db.types import Severity


def create(
    engine: Engine,
    *,
    name: str,
    description: str | None = None,
) -> Severity | None:
    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT OR IGNORE INTO severities (name, description, archived)
                VALUES (:name, :description, 0)
            """),
            {"name": name, "description": description},
        )
        conn.commit()
    return _get(engine, name)


def list_severities(
    engine: Engine, include_archived: bool = False
) -> list[Severity]:
    with engine.connect() as conn:
        sql = """
            SELECT s.name, s.description, s.archived,
                   COUNT(b.id) AS bug_count
            FROM severities s
            LEFT JOIN bugs b ON b.severity = s.name
            {where}
            GROUP BY s.name
            ORDER BY s.name
        """
        where = "" if include_archived else "WHERE s.archived = 0"
        rows = conn.execute(text(sql.format(where=where))).fetchall()
    return [
        Severity(name=r[0], description=r[1], archived=bool(r[2]), bug_count=r[3])
        for r in rows
    ]


def rename(engine: Engine, old_name: str, new_name: str) -> Severity | None:
    """Rename a severity and update all bugs referencing the old name."""
    with engine.connect() as conn:
        conn.execute(
            text("UPDATE bugs SET severity=:new WHERE severity=:old"),
            {"new": new_name, "old": old_name},
        )
        conn.execute(
            text("UPDATE severities SET name=:new WHERE name=:old"),
            {"new": new_name, "old": old_name},
        )
        conn.commit()
    return _get(engine, new_name)


def archive(engine: Engine, name: str) -> Severity | None:
    """Archive a severity (hides it from the picker but preserves bug data)."""
    with engine.connect() as conn:
        conn.execute(
            text("UPDATE severities SET archived=1 WHERE name=:name"),
            {"name": name},
        )
        conn.commit()
    return _get(engine, name)


def _get(engine: Engine, name: str) -> Severity | None:
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT s.name, s.description, s.archived, COUNT(b.id)
                FROM severities s
                LEFT JOIN bugs b ON b.severity = s.name
                WHERE s.name = :name
                GROUP BY s.name
            """),
            {"name": name},
        ).fetchone()
    if row is None:
        return None
    return Severity(name=row[0], description=row[1], archived=bool(row[2]), bug_count=row[3])
