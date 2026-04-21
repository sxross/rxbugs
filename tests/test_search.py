"""Tests for ``db.search`` and ``db.connection``."""

from __future__ import annotations

import pytest

from db import artifacts as artifacts_repo
from db import bugs as bugs_repo
from db import relations as relations_repo
from db.connection import make_search_backend
from db.search import Fts5Backend


@pytest.fixture
def backend(engine):
    return Fts5Backend(engine)


def test_make_search_backend_selects_fts5_for_sqlite(engine):
    assert isinstance(make_search_backend(engine), Fts5Backend)


def test_make_search_backend_raises_for_unsupported_dialect():
    class _StubDialect:
        name = "mysql"

    class _StubEngine:
        dialect = _StubDialect()

    with pytest.raises(ValueError, match="Unsupported database dialect"):
        make_search_backend(_StubEngine())  # type: ignore[arg-type]


def test_query_defaults_to_open_bugs(engine, backend):
    a = bugs_repo.create(engine, product="P", title="open one", actor="u", actor_type="human")
    b = bugs_repo.create(engine, product="P", title="closed one", actor="u", actor_type="human")
    bugs_repo.close(engine, b["id"], resolution="fixed", actor="u", actor_type="human")
    results = backend.query({})
    ids = [r["id"] for r in results]
    assert a["id"] in ids
    assert b["id"] not in ids


def test_query_status_all(engine, backend):
    a = bugs_repo.create(engine, product="P", title="o", actor="u", actor_type="human")
    b = bugs_repo.create(engine, product="P", title="c", actor="u", actor_type="human")
    bugs_repo.close(engine, b["id"], resolution="fixed", actor="u", actor_type="human")
    results = backend.query({"status": "all"})
    ids = {r["id"] for r in results}
    assert {a["id"], b["id"]} <= ids


def test_query_fts_matches_title(engine, backend):
    bugs_repo.create(engine, product="P", title="Memo card crashes", actor="u", actor_type="human")
    bugs_repo.create(engine, product="P", title="Unrelated issue", actor="u", actor_type="human")
    results = backend.query({"q": "memo"})
    titles = [r["title"] for r in results]
    assert "Memo card crashes" in titles
    assert "Unrelated issue" not in titles


def test_query_filters_product_and_priority(engine, backend):
    bugs_repo.create(engine, product="A", title="one", priority=1, actor="u", actor_type="human")
    bugs_repo.create(engine, product="B", title="two", priority=2, actor="u", actor_type="human")
    bugs_repo.create(engine, product="A", title="three", priority=3, actor="u", actor_type="human")

    results = backend.query({"product": ["A"], "priority": [1]})
    titles = [r["title"] for r in results]
    assert titles == ["one"]


def test_query_has_artifacts_filter(engine, backend):
    a = bugs_repo.create(engine, product="P", title="with", actor="u", actor_type="human")
    bugs_repo.create(engine, product="P", title="without", actor="u", actor_type="human")
    artifacts_repo.create(
        engine, bug_id=a["id"], filename="f", path="p",
        mime_type=None, actor="u", actor_type="human",
    )

    with_art = [r["title"] for r in backend.query({"has_artifacts": True})]
    without_art = [r["title"] for r in backend.query({"has_artifacts": False})]
    assert "with" in with_art and "without" not in with_art
    assert "without" in without_art and "with" not in without_art


def test_query_related_to(engine, backend):
    a = bugs_repo.create(engine, product="P", title="left", actor="u", actor_type="human")
    b = bugs_repo.create(engine, product="P", title="right", actor="u", actor_type="human")
    bugs_repo.create(engine, product="P", title="other", actor="u", actor_type="human")
    relations_repo.link(engine, a["id"], b["id"], actor="u", actor_type="human")
    results = backend.query({"related_to": a["id"]})
    assert [r["id"] for r in results] == [b["id"]]


def test_query_date_range(engine, backend):
    bug = bugs_repo.create(engine, product="P", title="dated", actor="u", actor_type="human")
    # Match on same created_at ISO timestamp we just received.
    ts = bug["created_at"]
    assert backend.query({"created_after": ts, "created_before": ts})


def test_index_remove_and_update_artifacts(engine, backend):
    bug = bugs_repo.create(engine, product="P", title="t", actor="u", actor_type="human")
    backend.update_artifacts(bug["id"], ["log.txt", "screenshot.png"])
    matches = backend.query({"q": "screenshot"})
    assert any(r["id"] == bug["id"] for r in matches)

    # Re-indexing a non-existent bug is a no-op (it simply re-runs the trigger).
    backend.index_bug(bug["id"])

    backend.remove_bug(bug["id"])
    # After remove from FTS table, text-based query stops returning it.
    assert not backend.query({"q": "screenshot"})
