"""Tests for ``db.artifacts``."""

from __future__ import annotations

from sqlalchemy import text

from db import artifacts as artifacts_repo
from db import bugs as bugs_repo


def _bug(engine):
    return bugs_repo.create(
        engine, product="X", title="T", actor="a", actor_type="human",
    )


def test_create_artifact(engine):
    bug = _bug(engine)
    art = artifacts_repo.create(
        engine, bug_id=bug["id"], filename="log.txt",
        path=f"{bug['id']}/log.txt", mime_type="text/plain",
        actor="a", actor_type="human",
    )
    assert art["id"] >= 1
    assert art["bug_id"] == bug["id"]
    assert art["filename"] == "log.txt"
    assert art["mime_type"] == "text/plain"


def test_create_refreshes_artifact_filenames_column(engine):
    bug = _bug(engine)
    artifacts_repo.create(
        engine, bug_id=bug["id"], filename="one.txt",
        path=f"{bug['id']}/one.txt", mime_type=None,
        actor="a", actor_type="human",
    )
    artifacts_repo.create(
        engine, bug_id=bug["id"], filename="two.png",
        path=f"{bug['id']}/two.png", mime_type="image/png",
        actor="a", actor_type="human",
    )
    with engine.connect() as conn:
        names = conn.execute(
            text("SELECT artifact_filenames FROM bugs WHERE id=:id"),
            {"id": bug["id"]},
        ).fetchone()[0]
    assert "one.txt" in names
    assert "two.png" in names


def test_get_returns_none_for_unknown(engine):
    assert artifacts_repo.get(engine, 9999) is None


def test_get_round_trip(engine):
    bug = _bug(engine)
    art = artifacts_repo.create(
        engine, bug_id=bug["id"], filename="x", path="p",
        mime_type=None, actor="a", actor_type="human",
    )
    assert artifacts_repo.get(engine, art["id"]) == art


def test_list_for_bug(engine):
    bug = _bug(engine)
    artifacts_repo.create(
        engine, bug_id=bug["id"], filename="a", path="a",
        mime_type=None, actor="x", actor_type="human",
    )
    artifacts_repo.create(
        engine, bug_id=bug["id"], filename="b", path="b",
        mime_type=None, actor="x", actor_type="human",
    )
    arts = artifacts_repo.list_for_bug(engine, bug["id"])
    assert [a["filename"] for a in arts] == ["a", "b"]


def test_audit_log_records_artifact_added(engine):
    bug = _bug(engine)
    artifacts_repo.create(
        engine, bug_id=bug["id"], filename="logs.txt",
        path="logs.txt", mime_type=None,
        actor="alice", actor_type="human",
    )
    with engine.connect() as conn:
        entry = conn.execute(
            text(
                "SELECT actor, field, new_value FROM audit_log "
                "WHERE bug_id=:id AND field='artifact_added'"
            ),
            {"id": bug["id"]},
        ).fetchone()
    assert entry is not None
    assert entry[0] == "alice"
    assert entry[2] == "logs.txt"
