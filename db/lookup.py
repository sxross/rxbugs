"""Generic lookup-table repository.

Products, Areas, Severities, and Platforms all share the same shape:
(name TEXT PK, description TEXT, archived INTEGER).  This module
provides a single reusable class so the four repo files become
thin wrappers with no duplicated SQL.
"""

from __future__ import annotations

from typing import TypeVar

from sqlalchemy import Engine, text

from db.types import Area, Platform, Product, Severity

# Every lookup TypedDict has the same four keys.
T = TypeVar("T", Product, Area, Severity, Platform)


class LookupRepo:
    """CRUD operations for an admin-managed lookup table.

    Parameters
    ----------
    table:
        SQL table name (e.g. ``"products"``).
    bug_field:
        Column name on the ``bugs`` table that references this lookup
        (e.g. ``"product"``).  Used for the JOIN in ``list`` and for
        cascading renames.
    type_factory:
        The TypedDict constructor (``Product``, ``Area``, …).
    """

    def __init__(self, table: str, bug_field: str, type_factory: type[T]) -> None:
        self._table = table
        self._bug_field = bug_field
        self._factory = type_factory

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create(
        self,
        engine: Engine,
        *,
        name: str,
        description: str | None = None,
    ) -> T | None:
        with engine.connect() as conn:
            conn.execute(
                text(
                    f"INSERT OR IGNORE INTO {self._table} "
                    f"(name, description, archived) VALUES (:name, :description, 0)"
                ),
                {"name": name, "description": description},
            )
            conn.commit()
        return self.get(engine, name)

    def list(
        self,
        engine: Engine,
        include_archived: bool = False,
    ) -> list[T]:
        where = "" if include_archived else f"WHERE t.archived = 0"
        sql = f"""
            SELECT t.name, t.description, t.archived,
                   COUNT(b.id) AS bug_count
            FROM {self._table} t
            LEFT JOIN bugs b ON b.{self._bug_field} = t.name
            {where}
            GROUP BY t.name
            ORDER BY t.name
        """
        with engine.connect() as conn:
            rows = conn.execute(text(sql)).fetchall()
        return [
            self._factory(
                name=r[0], description=r[1], archived=bool(r[2]), bug_count=r[3],
            )
            for r in rows
        ]

    def rename(
        self,
        engine: Engine,
        old_name: str,
        new_name: str,
    ) -> T | None:
        """Rename an entry and cascade to all bugs referencing the old name."""
        with engine.connect() as conn:
            conn.execute(
                text(
                    f"UPDATE bugs SET {self._bug_field}=:new "
                    f"WHERE {self._bug_field}=:old"
                ),
                {"new": new_name, "old": old_name},
            )
            conn.execute(
                text(
                    f"UPDATE {self._table} SET name=:new WHERE name=:old"
                ),
                {"new": new_name, "old": old_name},
            )
            conn.commit()
        return self.get(engine, new_name)

    def archive(self, engine: Engine, name: str) -> T | None:
        """Archive an entry (hides from pickers but preserves bug data)."""
        with engine.connect() as conn:
            conn.execute(
                text(f"UPDATE {self._table} SET archived=1 WHERE name=:name"),
                {"name": name},
            )
            conn.commit()
        return self.get(engine, name)

    def get(self, engine: Engine, name: str) -> T | None:
        """Return a single entry by name, or ``None``."""
        sql = f"""
            SELECT t.name, t.description, t.archived, COUNT(b.id)
            FROM {self._table} t
            LEFT JOIN bugs b ON b.{self._bug_field} = t.name
            WHERE t.name = :name
            GROUP BY t.name
        """
        with engine.connect() as conn:
            row = conn.execute(text(sql), {"name": name}).fetchone()
        if row is None:
            return None
        return self._factory(
            name=row[0], description=row[1], archived=bool(row[2]), bug_count=row[3],
        )


# ---------------------------------------------------------------------------
# Module-level singleton instances (importable by name)
# ---------------------------------------------------------------------------

products_repo = LookupRepo("products", "product", Product)
areas_repo = LookupRepo("areas", "area", Area)
severities_repo = LookupRepo("severities", "severity", Severity)
platforms_repo = LookupRepo("platforms", "platform", Platform)
