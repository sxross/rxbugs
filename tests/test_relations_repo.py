"""Tests for ``db.relations``."""

from __future__ import annotations

import pytest

from db import bugs as bugs_repo
from db import relations as relations_repo


def _two_bugs(engine):
    a = bugs_repo.create(engine, product="X", title="A", actor="u", actor_type="human")
    b = bugs_repo.create(engine, product="X", title="B", actor="u", actor_type="human")
    return a["id"], b["id"]


def test_link_creates_bidirectional_visibility(engine):
    a, b = _two_bugs(engine)
    relations_repo.link(engine, a, b, actor="u", actor_type="human")
    assert relations_repo.list_for_bug(engine, a) == [b]
    assert relations_repo.list_for_bug(engine, b) == [a]


def test_link_self_raises(engine):
    a, _ = _two_bugs(engine)
    with pytest.raises(ValueError, match="cannot be related to itself"):
        relations_repo.link(engine, a, a, actor="u", actor_type="human")


def test_link_is_idempotent(engine):
    a, b = _two_bugs(engine)
    relations_repo.link(engine, a, b, actor="u", actor_type="human")
    relations_repo.link(engine, b, a, actor="u", actor_type="human")  # reverse args
    related = relations_repo.list_for_bug(engine, a)
    assert related == [b]


def test_unlink_removes_relation(engine):
    a, b = _two_bugs(engine)
    relations_repo.link(engine, a, b, actor="u", actor_type="human")
    assert relations_repo.unlink(engine, a, b, actor="u", actor_type="human") is True
    assert relations_repo.list_for_bug(engine, a) == []


def test_unlink_missing_returns_false(engine):
    a, b = _two_bugs(engine)
    assert relations_repo.unlink(engine, a, b, actor="u", actor_type="human") is False


def test_list_for_bug_empty(engine):
    a, _ = _two_bugs(engine)
    assert relations_repo.list_for_bug(engine, a) == []
