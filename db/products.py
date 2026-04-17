"""Products repository — controlled product list management."""

from __future__ import annotations

from sqlalchemy import Engine, text

from db.types import Product


def create(
    engine: Engine,
    *,
    name: str,
    description: str | None = None,
) -> Product:
    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT OR IGNORE INTO products (name, description, archived)
                VALUES (:name, :description, 0)
            """),
            {"name": name, "description": description},
        )
        conn.commit()
    return _get(engine, name)  # type: ignore[return-value]


def list_products(engine: Engine, include_archived: bool = False) -> list[Product]:
    with engine.connect() as conn:
        sql = """
            SELECT p.name, p.description, p.archived,
                   COUNT(b.id) AS bug_count
            FROM products p
            LEFT JOIN bugs b ON b.product = p.name
            {where}
            GROUP BY p.name
            ORDER BY p.name
        """
        where = "" if include_archived else "WHERE p.archived = 0"
        rows = conn.execute(text(sql.format(where=where))).fetchall()
    return [
        Product(name=r[0], description=r[1], archived=bool(r[2]), bug_count=r[3])
        for r in rows
    ]


def rename(engine: Engine, old_name: str, new_name: str) -> Product | None:
    """Rename a product and update all bugs referencing the old name."""
    with engine.connect() as conn:
        conn.execute(
            text("UPDATE bugs SET product=:new WHERE product=:old"),
            {"new": new_name, "old": old_name},
        )
        conn.execute(
            text("UPDATE products SET name=:new WHERE name=:old"),
            {"new": new_name, "old": old_name},
        )
        conn.commit()
    return _get(engine, new_name)


def archive(engine: Engine, name: str) -> Product | None:
    """Archive a product (hides it from autocomplete but preserves bug data)."""
    with engine.connect() as conn:
        conn.execute(
            text("UPDATE products SET archived=1 WHERE name=:name"),
            {"name": name},
        )
        conn.commit()
    return _get(engine, name)


def _get(engine: Engine, name: str) -> Product | None:
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT p.name, p.description, p.archived, COUNT(b.id)
                FROM products p
                LEFT JOIN bugs b ON b.product = p.name
                WHERE p.name = :name
                GROUP BY p.name
            """),
            {"name": name},
        ).fetchone()
    if row is None:
        return None
    return Product(name=row[0], description=row[1], archived=bool(row[2]), bug_count=row[3])
