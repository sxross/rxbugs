"""API integration tests — agent registration, auth, and revocation."""

from __future__ import annotations

from tests.api_helpers import create_bug


def test_register_list_revoke_agent(client, auth_headers):
    # Register
    resp = client.post(
        "/agents", json={"name": "runner"}, headers=auth_headers,
    )
    assert resp.status_code == 201
    agent = resp.get_json()
    assert agent["key"].startswith("agt_")

    # List
    listed = client.get("/agents", headers=auth_headers).get_json()
    assert any(a["name"] == "runner" for a in listed)

    # The agent key should also authenticate other requests.
    agent_headers = {"Authorization": f"Bearer {agent['key']}"}
    assert client.get("/bugs", headers=agent_headers).status_code == 200

    # Revoke
    resp = client.delete(f"/agents/{agent['key']}", headers=auth_headers)
    assert resp.status_code == 204
    # After revoke the key can no longer authenticate.
    assert client.get("/bugs", headers=agent_headers).status_code == 401


def test_register_agent_requires_name(client, auth_headers):
    resp = client.post("/agents", json={}, headers=auth_headers)
    assert resp.status_code == 400


def test_revoke_unknown_agent_returns_404(client, auth_headers):
    resp = client.delete("/agents/agt_missing", headers=auth_headers)
    assert resp.status_code == 404


def test_agent_created_bugs_record_agent_actor_type(client, auth_headers, flask_app):
    agent = client.post(
        "/agents", json={"name": "r"}, headers=auth_headers,
    ).get_json()
    headers = {"Authorization": f"Bearer {agent['key']}"}
    resp = client.post(
        "/bugs", json={"product": "P", "title": "t"}, headers=headers,
    )
    bug = resp.get_json()

    # Inspect the audit log directly via the app's engine.
    from sqlalchemy import text
    with flask_app._engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT actor, actor_type FROM audit_log "
                "WHERE bug_id=:id AND field='created'"
            ),
            {"id": bug["id"]},
        ).fetchone()
    assert row == ("r", "agent")
