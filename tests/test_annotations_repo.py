"""Tests for ``db.annotations``."""

from __future__ import annotations

from sqlalchemy import text

from db import annotations as annotations_repo
from db import bugs as bugs_repo


def _bug(engine):
    return bugs_repo.create(
        engine, product="X", title="T", actor="a", actor_type="human",
    )


def test_create_annotation_returns_dict(engine):
    bug = _bug(engine)
    ann = annotations_repo.create(
        engine, bug_id=bug["id"], author="alice",
        author_type="human", body="Looks good",
    )
    assert ann["id"] >= 1
    assert ann["bug_id"] == bug["id"]
    assert ann["author"] == "alice"
    assert ann["body"] == "Looks good"


def test_create_annotation_sanitizes_body(engine):
    bug = _bug(engine)
    ann = annotations_repo.create(
        engine, bug_id=bug["id"], author="a",
        author_type="human",
        body="Hello <script>evil()</script>",
    )
    assert "<script>" not in ann["body"]


def test_create_updates_bug_updated_at(engine):
    bug = _bug(engine)
    annotations_repo.create(
        engine, bug_id=bug["id"], author="a", author_type="human", body="hi",
    )
    refreshed = bugs_repo.get(engine, bug["id"])
    assert refreshed["updated_at"] >= bug["updated_at"]


def test_list_for_bug_is_ordered(engine):
    bug = _bug(engine)
    for i in range(3):
        annotations_repo.create(
            engine, bug_id=bug["id"], author="a",
            author_type="human", body=f"body-{i}",
        )
    entries = annotations_repo.list_for_bug(engine, bug["id"])
    assert len(entries) == 3
    assert [e["body"] for e in entries] == ["body-0", "body-1", "body-2"]


def test_list_for_bug_empty(engine):
    bug = _bug(engine)
    assert annotations_repo.list_for_bug(engine, bug["id"]) == []


def test_annotation_appends_audit_log(engine):
    bug = _bug(engine)
    annotations_repo.create(
        engine, bug_id=bug["id"], author="a",
        author_type="human", body="hello",
    )
    with engine.connect() as conn:
        fields = [r[0] for r in conn.execute(
            text("SELECT field FROM audit_log WHERE bug_id=:id"),
            {"id": bug["id"]},
        ).fetchall()]
    assert "annotation_added" in fields
