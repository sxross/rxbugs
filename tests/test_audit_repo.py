"""Tests for ``db.audit``."""

from __future__ import annotations

from sqlalchemy import text

from db import audit
from db import bugs as bugs_repo


def _bug(engine):
    return bugs_repo.create(
        engine, product="X", title="T", actor="a", actor_type="human",
    )


def test_append_without_conn(engine):
    bug = _bug(engine)
    audit.append(
        engine,
        bug_id=bug["id"],
        actor="bob",
        actor_type="human",
        field="manual",
        old_value="old",
        new_value="new",
    )
    with engine.connect() as conn:
        entry = conn.execute(
            text(
                "SELECT actor, actor_type, field, old_value, new_value "
                "FROM audit_log WHERE field='manual'"
            )
        ).fetchone()
    assert entry == ("bob", "human", "manual", "old", "new")


def test_append_with_explicit_conn_shares_transaction(engine):
    bug = _bug(engine)
    with engine.connect() as conn:
        audit.append(
            engine,
            bug_id=bug["id"],
            actor="alice",
            actor_type="agent",
            field="in_txn",
            new_value="v",
            conn=conn,
        )
        # Before commit, nothing visible in a fresh connection:
        with engine.connect() as other:
            seen = other.execute(
                text("SELECT count(*) FROM audit_log WHERE field='in_txn'")
            ).fetchone()[0]
        assert seen == 0
        conn.commit()

    with engine.connect() as conn:
        seen_after = conn.execute(
            text("SELECT count(*) FROM audit_log WHERE field='in_txn'")
        ).fetchone()[0]
    assert seen_after == 1
