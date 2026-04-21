"""Tests for ``db.agents``."""

from __future__ import annotations

from db import agents as agents_repo


def test_register_returns_agent_and_key(engine):
    agent, key = agents_repo.register(
        engine, name="ci-runner", description="CI agent",
    )
    assert agent["name"] == "ci-runner"
    assert agent["description"] == "CI agent"
    assert agent["active"] is True
    assert agent["key"] == key
    assert key.startswith("agt_")


def test_authenticate_active_agent(engine):
    _, key = agents_repo.register(engine, name="a")
    agent = agents_repo.authenticate(engine, key)
    assert agent is not None
    assert agent["name"] == "a"


def test_authenticate_unknown_key_returns_none(engine):
    assert agents_repo.authenticate(engine, "agt_nope") is None


def test_authenticate_inactive_agent_returns_none(engine):
    _, key = agents_repo.register(engine, name="a")
    agents_repo.revoke(engine, key)
    assert agents_repo.authenticate(engine, key) is None


def test_get_rate_limit_default_for_unknown(engine):
    assert agents_repo.get_rate_limit(engine, "agt_nope") == 60


def test_get_rate_limit_custom(engine):
    _, key = agents_repo.register(engine, name="a", rate_limit=5)
    assert agents_repo.get_rate_limit(engine, key) == 5


def test_list_agents(engine):
    agents_repo.register(engine, name="one")
    agents_repo.register(engine, name="two")
    listed = agents_repo.list_agents(engine)
    assert {a["name"] for a in listed} == {"one", "two"}


def test_revoke_returns_true_for_existing(engine):
    _, key = agents_repo.register(engine, name="a")
    assert agents_repo.revoke(engine, key) is True


def test_revoke_returns_false_for_missing(engine):
    assert agents_repo.revoke(engine, "agt_nope") is False


def test_revoke_marks_agent_inactive(engine):
    _, key = agents_repo.register(engine, name="a")
    agents_repo.revoke(engine, key)
    agents = agents_repo.list_agents(engine)
    revoked = next(a for a in agents if a["key"] == key)
    assert revoked["active"] is False
