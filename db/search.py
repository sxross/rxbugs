"""Full-text search abstraction.

Routes call SearchBackend methods and never know which database is running.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from sqlalchemy import Engine, text

if TYPE_CHECKING:
    from db.types import BugFilters, BugSummary


@runtime_checkable
class SearchBackend(Protocol):
    def query(self, filters: "BugFilters") -> list["BugSummary"]: ...
    def index_bug(self, bug_id: str) -> None: ...
    def update_artifacts(self, bug_id: str, filenames: list[str]) -> None: ...
    def remove_bug(self, bug_id: str) -> None: ...


class Fts5Backend:
    """SQLite FTS5 implementation."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def query(self, filters: "BugFilters") -> list["BugSummary"]:
        """Run a filtered search against bugs + FTS5 index."""
        conditions: list[str] = []
        params: dict = {}

        # Full-text query — use FTS5 MATCH if text is provided
        fts_join = ""
        if filters.get("q"):
            # Escape single quotes in the query string for FTS5
            q = str(filters["q"]).replace('"', '""')
            params["fts_query"] = f'"{q}"*'
            fts_join = (
                "JOIN bugs_fts ON bugs_fts.id = bugs.id "
                "AND bugs_fts MATCH :fts_query"
            )

        # related_to — join through bug_relations (both directions)
        related_join = ""
        if filters.get("related_to"):
            params["related_to"] = filters["related_to"]
            related_join = (
                "JOIN bug_relations br ON "
                "(br.bug_id = bugs.id AND br.related_id = :related_to) OR "
                "(br.related_id = bugs.id AND br.bug_id = :related_to)"
            )

        # has_artifacts
        if "has_artifacts" in filters:
            if filters["has_artifacts"]:
                conditions.append(
                    "EXISTS (SELECT 1 FROM artifacts WHERE artifacts.bug_id = bugs.id)"
                )
            else:
                conditions.append(
                    "NOT EXISTS (SELECT 1 FROM artifacts WHERE artifacts.bug_id = bugs.id)"
                )

        # status (default open)
        status = filters.get("status", "open")
        if status != "all":
            conditions.append("bugs.status = :status")
            params["status"] = status

        # Multi-value filters
        def _in_filter(field: str, key: str, values: list) -> None:
            placeholders = ", ".join(f":{key}_{i}" for i in range(len(values)))
            conditions.append(f"bugs.{field} IN ({placeholders})")
            for i, v in enumerate(values):
                params[f"{key}_{i}"] = v

        if filters.get("product"):
            _in_filter("product", "product", filters["product"])  # type: ignore[arg-type]
        if filters.get("area"):
            _in_filter("area", "area", filters["area"])  # type: ignore[arg-type]
        if filters.get("priority"):
            _in_filter("priority", "priority", filters["priority"])  # type: ignore[arg-type]
        if filters.get("severity"):
            _in_filter("severity", "severity", filters["severity"])  # type: ignore[arg-type]
        if filters.get("resolution"):
            _in_filter("resolution", "resolution", filters["resolution"])  # type: ignore[arg-type]

        # Date range filters
        if filters.get("created_after"):
            conditions.append("bugs.created_at >= :created_after")
            params["created_after"] = filters["created_after"]
        if filters.get("created_before"):
            conditions.append("bugs.created_at <= :created_before")
            params["created_before"] = filters["created_before"]

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        sql = f"""
            SELECT
                bugs.id, bugs.product, bugs.title,
                bugs.area, bugs.priority, bugs.severity,
                bugs.status, bugs.resolution,
                bugs.created_at, bugs.updated_at
            FROM bugs
            {fts_join}
            {related_join}
            {where_clause}
            ORDER BY bugs.created_at DESC
        """

        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), params).fetchall()

        return [_row_to_summary(r) for r in rows]

    def index_bug(self, bug_id: str) -> None:
        """Rebuild the FTS row for a single bug (called after artifact changes)."""
        with self._engine.connect() as conn:
            self._refresh_fts(conn, bug_id)
            conn.commit()

    def update_artifacts(self, bug_id: str, filenames: list[str]) -> None:
        """Update artifact_filenames on the bugs row (FTS trigger keeps index in sync)."""
        joined = " ".join(filenames)
        with self._engine.connect() as conn:
            conn.execute(
                text("UPDATE bugs SET artifact_filenames = :names WHERE id = :id"),
                {"names": joined, "id": bug_id},
            )
            conn.commit()

    def remove_bug(self, bug_id: str) -> None:
        with self._engine.connect() as conn:
            conn.execute(
                text("DELETE FROM bugs_fts WHERE id = :id"), {"id": bug_id}
            )
            conn.commit()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _refresh_fts(self, conn, bug_id: str) -> None:
        """Re-sync artifact_filenames on the bugs row (FTS trigger handles index)."""
        filenames_row = conn.execute(
            text(
                "SELECT GROUP_CONCAT(filename, ' ') FROM artifacts WHERE bug_id = :id"
            ),
            {"id": bug_id},
        ).fetchone()
        filenames = filenames_row[0] or "" if filenames_row else ""
        conn.execute(
            text("UPDATE bugs SET artifact_filenames = :f WHERE id = :id"),
            {"f": filenames, "id": bug_id},
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row_to_summary(row) -> "BugSummary":
    from db.types import BugSummary  # local import to avoid circular deps

    return BugSummary(
        id=row[0],
        product=row[1],
        title=row[2],
        area=row[3],
        priority=row[4],
        severity=row[5],
        status=row[6],
        resolution=row[7],
        created_at=row[8],
        updated_at=row[9],
    )
