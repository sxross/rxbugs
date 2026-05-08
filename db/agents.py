"""Agent repository — registration, authentication, revocation."""

from __future__ import annotations

import secrets
import string
from datetime import datetime, timezone

from sqlalchemy import Engine, text

from db.types import Agent

AGENT_KEY_CHARS = string.ascii_letters + string.digits
AGENT_KEY_LEN = 12
AGENT_KEY_PREFIX = "agt_"
DEFAULT_RATE_LIMIT = 60


def _generate_key() -> str:
    return AGENT_KEY_PREFIX + "".join(
        secrets.choice(AGENT_KEY_CHARS) for _ in range(AGENT_KEY_LEN)
    )


def register(
    engine: Engine,
    *,
    name: str,
    description: str | None = None,
    rate_limit: int = DEFAULT_RATE_LIMIT,
) -> tuple[Agent, str]:
    """Register a new agent.

    Returns ``(Agent, raw_key)``.  The raw key is shown to the caller once
    and never stored in plain text — the DB stores it directly (no hashing
    needed for local-only use; add bcrypt here when moving to a shared host).
    """
    key = _generate_key()
    now = datetime.now(timezone.utc).isoformat()
    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT INTO agents (key, name, description, created_at, active, rate_limit)
                VALUES (:key, :name, :description, :created_at, 1, :rate_limit)
            """),
            {
                "key": key,
                "name": name,
                "description": description,
                "created_at": now,
                "rate_limit": rate_limit,
            },
        )
        conn.commit()
    agent: Agent = {
        "key": key,
        "name": name,
        "description": description,
        "created_at": now,
        "active": True,
    }
    return agent, key


def authenticate(engine: Engine, key: str) -> Agent | None:
    """Return the Agent if the key is valid and active, else None."""
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT key, name, description, created_at, active FROM agents WHERE key = :key"),
            {"key": key},
        ).fetchone()
    if row is None or not row[4]:
        return None
    return Agent(
        key=row[0],
        name=row[1],
        description=row[2],
        created_at=row[3],
        active=bool(row[4]),
    )


def get_rate_limit(engine: Engine, key: str) -> int:
    """Return the per-minute rate limit for the given agent key."""
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT rate_limit FROM agents WHERE key = :key"),
            {"key": key},
        ).fetchone()
    return row[0] if row else DEFAULT_RATE_LIMIT


def list_agents(engine: Engine) -> list[Agent]:
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT key, name, description, created_at, active FROM agents ORDER BY created_at")
        ).fetchall()
    return [
        Agent(key=r[0], name=r[1], description=r[2], created_at=r[3], active=bool(r[4]))
        for r in rows
    ]


def revoke(engine: Engine, key: str) -> bool:
    """Revoke an agent key.  Returns True if the key existed."""
    with engine.connect() as conn:
        result = conn.execute(
            text("UPDATE agents SET active = 0 WHERE key = :key"),
            {"key": key},
        )
        conn.commit()
    return result.rowcount > 0
