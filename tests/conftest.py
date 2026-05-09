"""Shared pytest fixtures for RxBugs.

Strategy
--------
* Repository tests get a fresh SQLite database per test via the ``engine``
  fixture (Alembic ``upgrade head`` is run every time).
* API tests share one Flask app (because ``app.py`` creates its engine and
  search backend at import time) and wipe the mutable tables between tests.
* ``BUGTRACKER_TOKEN`` and ``DATABASE_URL`` are set **before** any test
  imports ``app`` so the module-level pre-flight check passes.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

# ---------------------------------------------------------------------------
# One-time environment setup (must happen before ``import app``)
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Make the project root importable when pytest is run from elsewhere.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# A dedicated DB file for the session-scoped Flask app.
_SESSION_DIR = Path(tempfile.mkdtemp(prefix="rxbugs-tests-"))
_API_DB_PATH = _SESSION_DIR / "api.db"

os.environ["BUGTRACKER_TOKEN"] = "test-token-please-ignore"
os.environ["DATABASE_URL"] = f"sqlite:///{_API_DB_PATH}"
os.environ["RUN_MIGRATIONS"] = "true"

# Ensure app doesn't accidentally read the developer's .env
# (load_dotenv is a no-op if the vars are already set, but belt + suspenders).
os.environ.setdefault("BUGTRACKER_HOST", "127.0.0.1")
os.environ.setdefault("BUGTRACKER_PORT", "5000")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_migrations(url: str) -> None:
    """Run Alembic ``upgrade head`` against *url*.

    ``alembic/env.py`` unconditionally reads ``DATABASE_URL`` from the
    environment (and overrides the value set on the :class:`AlembicConfig`),
    so we have to temporarily patch the env var for the duration of the call.
    """
    from alembic import command as alembic_command
    from alembic.config import Config as AlembicConfig

    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    try:
        cfg = AlembicConfig(str(PROJECT_ROOT / "alembic.ini"))
        cfg.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
        cfg.set_main_option("sqlalchemy.url", url)
        alembic_command.upgrade(cfg, "head")
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous



# Seed data
_SEED_AREAS = ["ui", "middleware", "backend", "database", "sync"]
_SEED_SEVERITIES = ["showstopper", "serious", "enhancement", "nice_to_have"]
_SEED_PLATFORMS = ["iOS", "Android", "Web", "macOS", "Windows", "Linux"]


def _reseed_lookup_tables(engine) -> None:
    with engine.connect() as conn:
        for name in _SEED_AREAS:
            conn.execute(
                text("INSERT OR IGNORE INTO areas (name, description, archived) VALUES (:n, NULL, 0)"),
                {"n": name},
            )
        for name in _SEED_SEVERITIES:
            conn.execute(
                text("INSERT OR IGNORE INTO severities (name, description, archived) VALUES (:n, NULL, 0)"),
                {"n": name},
            )
        for name in _SEED_PLATFORMS:
            conn.execute(
                text("INSERT OR IGNORE INTO platforms (name, description, archived) VALUES (:n, NULL, 0)"),
                {"n": name},
            )
        conn.commit()


def _wipe_db(engine) -> None:
    """Delete every row from every mutable table (keeps the schema)."""
    # Order matters: child tables before parents.
    tables = [
        "audit_log",
        "annotations",
        "artifacts",
        "bug_relations",
        "bugs",
        "agents",
        "areas",
        "severities",
        "platforms",
        "products",
    ]
    with engine.connect() as conn:
        for t in tables:
            conn.execute(text(f"DELETE FROM {t}"))
        # Rebuild FTS index now that its underlying content is empty.
        conn.execute(text("INSERT INTO bugs_fts(bugs_fts) VALUES('rebuild')"))
        # Reset AUTOINCREMENT counters so IDs are predictable between tests.
        conn.execute(text("DELETE FROM sqlite_sequence"))
        conn.commit()
    _reseed_lookup_tables(engine)


# ---------------------------------------------------------------------------
# Fixtures — repository layer
# ---------------------------------------------------------------------------

@pytest.fixture
def engine(tmp_path):
    """Fresh SQLite database with Alembic migrations applied.

    Uses :class:`NullPool` so each connection is opened fresh. SQLite's
    FTS5 virtual table only sees schema-change notifications within the
    connection that observed them; pooled connections can end up with
    stale state that manifests as ``database disk image is malformed``
    on subsequent writes.
    """
    db_path = tmp_path / "repo.db"
    url = f"sqlite:///{db_path}"
    _run_migrations(url)
    eng = create_engine(
        url,
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
    )
    try:
        yield eng
    finally:
        eng.dispose()


# ---------------------------------------------------------------------------
# Fixtures — Flask application (session-scoped)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def flask_app():
    """Import ``app`` exactly once after env vars are in place."""
    import app as flask_module  # noqa: WPS433 — deliberate runtime import

    # Disable Flask-Limiter so noisy test loops don't trip it.
    flask_module.limiter.enabled = False
    flask_module.app.config["TESTING"] = True
    return flask_module


@pytest.fixture
def client(flask_app):
    """Flask test client with a clean DB for every test."""
    _wipe_db(flask_app._engine)
    # Drop any pooled connections so the next ones see a fresh schema cache
    # (FTS5 + QueuePool interact poorly after cross-connection DDL/DML).
    flask_app._engine.dispose()
    with flask_app.app.test_client() as c:
        yield c


@pytest.fixture
def token() -> str:
    """The human/admin bearer token expected by ``app.py``."""
    return os.environ["BUGTRACKER_TOKEN"]


@pytest.fixture
def auth_headers(token):
    """Shortcut for ``Authorization: Bearer <token>``."""
    return {"Authorization": f"Bearer {token}"}
