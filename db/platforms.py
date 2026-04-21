"""Platforms repository — controlled platform list management.

Mirrors ``db/areas.py``. Platforms are user-defined labels
(e.g. "iOS", "Android", "Web") attached to bugs.
"""

from __future__ import annotations

from sqlalchemy import Engine, text

from db.types import Platform


def create(
    engine: Engine,
    *,
    name: str,
    description: str | None = None,
) -> Platform | None:
    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT OR IGNORE INTO platforms (name, description, archived)
                VALUES (:name, :description, 0)
            """),
            {"name": name, "description": description},
        )
        conn.commit()
    return _get(engine, name)


def list_platforms(
    engine: Engine, include_archived: bool = False
) -> list[Platform]:
    with engine.connect() as conn:
        sql = """
            SELECT p.name, p.description, p.archived,
                   COUNT(b.id) AS bug_count
            FROM platforms p
            LEFT JOIN bugs b ON b.platform = p.name
            {where}
            GROUP BY p.name
            ORDER BY p.name
        """
        where = "" if include_archived else "WHERE p.archived = 0"
        rows = conn.execute(text(sql.format(where=where))).fetchall()
    return [
        Platform(name=r[0], description=r[1], archived=bool(r[2]), bug_count=r[3])
        for r in rows
    ]


def rename(engine: Engine, old_name: str, new_name: str) -> Platform | None:
    """Rename a platform and update all bugs referencing the old name."""
    with engine.connect() as conn:
        conn.execute(
            text("UPDATE bugs SET platform=:new WHERE platform=:old"),
            {"new": new_name, "old": old_name},
        )
        conn.execute(
            text("UPDATE platforms SET name=:new WHERE name=:old"),
            {"new": new_name, "old": old_name},
        )
        conn.commit()
    return _get(engine, new_name)


def archive(engine: Engine, name: str) -> Platform | None:
    """Archive a platform (hides it from the picker but preserves bug data)."""
    with engine.connect() as conn:
        conn.execute(
            text("UPDATE platforms SET archived=1 WHERE name=:name"),
            {"name": name},
        )
        conn.commit()
    return _get(engine, name)


def _get(engine: Engine, name: str) -> Platform | None:
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT p.name, p.description, p.archived, COUNT(b.id)
                FROM platforms p
                LEFT JOIN bugs b ON b.platform = p.name
                WHERE p.name = :name
                GROUP BY p.name
            """),
            {"name": name},
        ).fetchone()
    if row is None:
        return None
    return Platform(name=row[0], description=row[1], archived=bool(row[2]), bug_count=row[3])
