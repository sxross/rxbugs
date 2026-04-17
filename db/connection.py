"""Database connection management.

A single Engine is created at startup and shared across all repositories.
The search backend is selected automatically based on the dialect.
"""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import Engine, create_engine

from db.search import Fts5Backend, SearchBackend

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

_DEFAULT_DB_PATH = Path(__file__).parent.parent / "bugtracker.db"
_DEFAULT_URL = f"sqlite:///{_DEFAULT_DB_PATH}"


def init_engine(url: str | None = None) -> Engine:
    """Create and return a SQLAlchemy Engine.

    If *url* is omitted the value of the ``DATABASE_URL`` environment
    variable is used, falling back to a local SQLite file.
    """
    connection_url = url or os.environ.get("DATABASE_URL", _DEFAULT_URL)
    kwargs: dict = {"echo": False}
    if connection_url.startswith("sqlite"):
        # Required for SQLite to work properly with multiple threads in Flask
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(connection_url, **kwargs)


# ---------------------------------------------------------------------------
# Search backend selector
# ---------------------------------------------------------------------------


def make_search_backend(engine: Engine) -> SearchBackend:
    """Return the appropriate SearchBackend for the connected database dialect."""
    dialect = engine.dialect.name
    if dialect == "sqlite":
        return Fts5Backend(engine)
    # PostgreSQL and MySQL backends are stubs for now; wire them in when needed.
    raise ValueError(
        f"Unsupported database dialect '{dialect}'. "
        "Currently only SQLite is supported. "
        "Set DATABASE_URL to a sqlite:// URL."
    )
