"""Tests for ``db.bugs``."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from db import bugs as bugs_repo


def _create(engine, **overrides):
    kwargs = dict(
        product="RxTrack",
        title="Test bug",
        actor="alice",
        actor_type="human",
    )
    kwargs.update(overrides)
    return bugs_repo.create(engine, **kwargs)


def test_create_returns_bug_with_defaults(engine):
    bug = _create(engine)
    assert bug["id"] == "BUG-0001"
    assert bug["product"] == "RxTrack"
    assert bug["title"] == "Test bug"
    assert bug["status"] == "open"
    assert bug["resolution"] == "none"
    assert bug["description"] is None
    assert bug["area"] is None
    assert bug["platform"] is None
    assert bug["priority"] is None
    assert bug["severity"] is None
    assert bug["created_at"] == bug["updated_at"]


def test_create_auto_increments_ids(engine):
    a = _create(engine)
    b = _create(engine, title="Second")
    c = _create(engine, title="Third")
    assert [a["id"], b["id"], c["id"]] == ["BUG-0001", "BUG-0002", "BUG-0003"]


def test_create_sanitizes_description(engine):
    bug = _create(engine, description="Hello <script>evil()</script> world")
    # <script> is not in the allow list; bleach escapes it.
    assert "<script>" not in bug["description"]
    assert "Hello" in bug["description"]


def test_create_ensures_related_lookup_rows(engine):
    _create(
        engine,
        product="NewProduct",
        area="cli",
        platform="watchOS",
        severity="critical",
    )
    with engine.connect() as conn:
        products = {r[0] for r in conn.execute(text("SELECT name FROM products")).fetchall()}
        areas = {r[0] for r in conn.execute(text("SELECT name FROM areas")).fetchall()}
        platforms = {r[0] for r in conn.execute(text("SELECT name FROM platforms")).fetchall()}
        severities = {r[0] for r in conn.execute(text("SELECT name FROM severities")).fetchall()}
    assert "NewProduct" in products
    assert "cli" in areas
    assert "watchOS" in platforms
    assert "critical" in severities


def test_get_returns_none_for_missing(engine):
    assert bugs_repo.get(engine, "BUG-9999") is None


def test_get_round_trip(engine):
    created = _create(engine, description="desc", priority=2)
    fetched = bugs_repo.get(engine, created["id"])
    assert fetched == created


def test_update_sets_fields_and_audits(engine):
    bug = _create(engine, title="Original")
    updated = bugs_repo.update(
        engine, bug["id"],
        actor="bob", actor_type="human",
        title="Renamed",
        priority=3,
        description="new desc",
    )
    assert updated["title"] == "Renamed"
    assert updated["priority"] == 3
    assert updated["description"] == "new desc"
    assert updated["updated_at"] >= bug["updated_at"]

    with engine.connect() as conn:
        entries = conn.execute(
            text("SELECT field, old_value, new_value FROM audit_log WHERE bug_id=:id ORDER BY id"),
            {"id": bug["id"]},
        ).fetchall()
    fields = [e[0] for e in entries]
    # The initial 'created' entry plus one per updated field (not updated_at).
    assert "title" in fields
    assert "priority" in fields
    assert "description" in fields
    assert "updated_at" not in fields


def test_update_ignores_unknown_fields(engine):
    bug = _create(engine)
    # ``foo`` is not in the mutable set — should be a no-op.
    result = bugs_repo.update(engine, bug["id"], actor="a", actor_type="human", foo="bar")
    assert result["title"] == bug["title"]


def test_update_missing_returns_none(engine):
    assert bugs_repo.update(
        engine, "BUG-9999", actor="a", actor_type="human", title="x"
    ) is None


def test_update_sanitizes_description(engine):
    bug = _create(engine, description="clean")
    updated = bugs_repo.update(
        engine, bug["id"], actor="a", actor_type="human",
        description="<script>bad()</script>ok",
    )
    assert "<script>" not in updated["description"]
    assert "ok" in updated["description"]


def test_close_sets_status_and_resolution(engine):
    bug = _create(engine)
    closed = bugs_repo.close(
        engine, bug["id"],
        resolution="fixed", actor="bob", actor_type="human",
    )
    assert closed["status"] == "closed"
    assert closed["resolution"] == "fixed"


def test_close_already_closed_raises(engine):
    bug = _create(engine)
    bugs_repo.close(engine, bug["id"], resolution="fixed", actor="a", actor_type="human")
    with pytest.raises(ValueError, match="already closed"):
        bugs_repo.close(engine, bug["id"], resolution="fixed", actor="a", actor_type="human")


def test_close_resolution_none_raises(engine):
    bug = _create(engine)
    with pytest.raises(ValueError, match="resolution is required"):
        bugs_repo.close(engine, bug["id"], resolution="none", actor="a", actor_type="human")


def test_close_missing_bug_returns_none(engine):
    assert bugs_repo.close(
        engine, "BUG-9999", resolution="fixed", actor="a", actor_type="human",
    ) is None


def test_reopen_resets_resolution(engine):
    bug = _create(engine)
    bugs_repo.close(engine, bug["id"], resolution="fixed", actor="a", actor_type="human")
    reopened = bugs_repo.reopen(engine, bug["id"], actor="a", actor_type="human")
    assert reopened["status"] == "open"
    assert reopened["resolution"] == "none"


def test_reopen_open_raises(engine):
    bug = _create(engine)
    with pytest.raises(ValueError, match="already open"):
        bugs_repo.reopen(engine, bug["id"], actor="a", actor_type="human")


def test_reopen_missing_bug_returns_none(engine):
    assert bugs_repo.reopen(
        engine, "BUG-9999", actor="a", actor_type="human",
    ) is None
