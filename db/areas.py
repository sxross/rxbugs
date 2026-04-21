"""Areas repository — controlled area list management.

Mirrors ``db/products.py``. Areas are user-defined categories
(e.g. "ui", "backend") that can be attached to bugs.
"""

from __future__ import annotations

from sqlalchemy import Engine, text

from db.types import Area


def create(
    engine: Engine,
    *,
    name: str,
    description: str | None = None,
) -> Area | None:
    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT OR IGNORE INTO areas (name, description, archived)
                VALUES (:name, :description, 0)
            """),
            {"name": name, "description": description},
        )
        conn.commit()
    return _get(engine, name)


def list_areas(engine: Engine, include_archived: bool = False) -> list[Area]:
    with engine.connect() as conn:
        sql = """
            SELECT a.name, a.description, a.archived,
                   COUNT(b.id) AS bug_count
            FROM areas a
            LEFT JOIN bugs b ON b.area = a.name
            {where}
            GROUP BY a.name
            ORDER BY a.name
        """
        where = "" if include_archived else "WHERE a.archived = 0"
        rows = conn.execute(text(sql.format(where=where))).fetchall()
    return [
        Area(name=r[0], description=r[1], archived=bool(r[2]), bug_count=r[3])
        for r in rows
    ]


def rename(engine: Engine, old_name: str, new_name: str) -> Area | None:
    """Rename an area and update all bugs referencing the old name."""
    with engine.connect() as conn:
        conn.execute(
            text("UPDATE bugs SET area=:new WHERE area=:old"),
            {"new": new_name, "old": old_name},
        )
        conn.execute(
            text("UPDATE areas SET name=:new WHERE name=:old"),
            {"new": new_name, "old": old_name},
        )
        conn.commit()
    return _get(engine, new_name)


def archive(engine: Engine, name: str) -> Area | None:
    """Archive an area (hides it from the picker but preserves bug data)."""
    with engine.connect() as conn:
        conn.execute(
            text("UPDATE areas SET archived=1 WHERE name=:name"),
            {"name": name},
        )
        conn.commit()
    return _get(engine, name)


def _get(engine: Engine, name: str) -> Area | None:
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT a.name, a.description, a.archived, COUNT(b.id)
                FROM areas a
                LEFT JOIN bugs b ON b.area = a.name
                WHERE a.name = :name
                GROUP BY a.name
            """),
            {"name": name},
        ).fetchone()
    if row is None:
        return None
    return Area(name=row[0], description=row[1], archived=bool(row[2]), bug_count=row[3])
