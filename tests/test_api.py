"""Integration tests for the Flask API defined in ``app.py``.

They use the session-scoped Flask app (see ``conftest.py``) and wipe the
database between tests so each test starts from a known, empty state
with only the seed lookup rows present.
"""

from __future__ import annotations

import io

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_bug(client, headers, **overrides):
    payload = {"product": "RxTrack", "title": "A bug"}
    payload.update(overrides)
    resp = client.post("/bugs", json=payload, headers=headers)
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def test_unauthorized_without_header(client):
    resp = client.get("/bugs")
    assert resp.status_code == 401
    assert resp.get_json() == {"error": "Unauthorized"}


def test_unauthorized_wrong_scheme(client):
    resp = client.get("/bugs", headers={"Authorization": "Basic abc"})
    assert resp.status_code == 401


def test_unauthorized_bad_token(client):
    resp = client.get("/bugs", headers={"Authorization": "Bearer wrong"})
    assert resp.status_code == 401


def test_index_serves_spa(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"<html" in resp.data.lower() or b"<!doctype" in resp.data.lower()


# ---------------------------------------------------------------------------
# Bugs: create / list / get / update
# ---------------------------------------------------------------------------

def test_create_bug_requires_product(client, auth_headers):
    resp = client.post("/bugs", json={"title": "t"}, headers=auth_headers)
    assert resp.status_code == 400
    assert "product" in resp.get_json()["error"]


def test_create_bug_requires_title(client, auth_headers):
    resp = client.post("/bugs", json={"product": "p"}, headers=auth_headers)
    assert resp.status_code == 400
    assert "title" in resp.get_json()["error"]


def test_create_bug_happy_path(client, auth_headers):
    bug = _create_bug(client, auth_headers, priority=1, severity="showstopper")
    assert bug["id"].startswith("BUG-")
    assert bug["status"] == "open"
    assert bug["priority"] == 1
    assert bug["severity"] == "showstopper"


def test_list_bugs_returns_total_and_list(client, auth_headers):
    _create_bug(client, auth_headers, title="first")
    _create_bug(client, auth_headers, title="second")
    resp = client.get("/bugs", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] == 2
    assert len(data["bugs"]) == 2


def test_list_bugs_with_priority_filter(client, auth_headers):
    _create_bug(client, auth_headers, title="p1", priority=1)
    _create_bug(client, auth_headers, title="p2", priority=2)
    resp = client.get("/bugs?priority=1", headers=auth_headers)
    assert resp.status_code == 200
    titles = [b["title"] for b in resp.get_json()["bugs"]]
    assert titles == ["p1"]


def test_list_bugs_invalid_priority(client, auth_headers):
    resp = client.get("/bugs?priority=notanumber", headers=auth_headers)
    assert resp.status_code == 400


def test_list_bugs_multi_valued_filter(client, auth_headers):
    _create_bug(client, auth_headers, title="a", area="ui")
    _create_bug(client, auth_headers, title="b", area="backend")
    _create_bug(client, auth_headers, title="c", area="sync")
    resp = client.get("/bugs?area=ui&area=backend", headers=auth_headers)
    titles = {b["title"] for b in resp.get_json()["bugs"]}
    assert titles == {"a", "b"}


def test_list_bugs_has_artifacts_filter(client, auth_headers):
    with_art = _create_bug(client, auth_headers, title="with")
    _create_bug(client, auth_headers, title="without")
    client.post(
        f"/bugs/{with_art['id']}/artifacts",
        data={"file": (io.BytesIO(b"hello"), "notes.txt")},
        headers=auth_headers,
        content_type="multipart/form-data",
    )
    resp = client.get("/bugs?has_artifacts=true", headers=auth_headers)
    titles = [b["title"] for b in resp.get_json()["bugs"]]
    assert titles == ["with"]


def test_get_bug_404(client, auth_headers):
    resp = client.get("/bugs/BUG-9999", headers=auth_headers)
    assert resp.status_code == 404


def test_get_bug_returns_annotations_and_artifacts(client, auth_headers):
    bug = _create_bug(client, auth_headers)
    client.post(
        f"/bugs/{bug['id']}/annotations",
        json={"body": "a comment"},
        headers=auth_headers,
    )
    resp = client.get(f"/bugs/{bug['id']}", headers=auth_headers)
    data = resp.get_json()
    assert data["id"] == bug["id"]
    assert isinstance(data["annotations"], list)
    assert isinstance(data["artifacts"], list)
    assert isinstance(data["related_bugs"], list)
    assert len(data["annotations"]) == 1


def test_update_bug(client, auth_headers):
    bug = _create_bug(client, auth_headers, title="old")
    resp = client.patch(
        f"/bugs/{bug['id']}",
        json={"title": "new", "priority": 2},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "new"
    assert resp.get_json()["priority"] == 2


def test_update_bug_404(client, auth_headers):
    resp = client.patch("/bugs/BUG-9999", json={"title": "x"}, headers=auth_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Close / Reopen
# ---------------------------------------------------------------------------

def test_close_requires_resolution(client, auth_headers):
    bug = _create_bug(client, auth_headers)
    resp = client.post(f"/bugs/{bug['id']}/close", json={}, headers=auth_headers)
    assert resp.status_code == 400


def test_close_bug_happy_path(client, auth_headers):
    bug = _create_bug(client, auth_headers)
    resp = client.post(
        f"/bugs/{bug['id']}/close",
        json={"resolution": "fixed", "annotation": "Done."},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["bug"]["status"] == "closed"
    assert payload["bug"]["resolution"] == "fixed"
    # No warnings if annotation provided.
    assert "warnings" not in payload


def test_close_fixed_without_annotation_returns_warning(client, auth_headers):
    bug = _create_bug(client, auth_headers)
    resp = client.post(
        f"/bugs/{bug['id']}/close",
        json={"resolution": "fixed"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert "warnings" in resp.get_json()


def test_close_duplicate_without_link_warns(client, auth_headers):
    bug = _create_bug(client, auth_headers)
    resp = client.post(
        f"/bugs/{bug['id']}/close",
        json={"resolution": "duplicate"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert any("duplicate" in w for w in resp.get_json()["warnings"])


def test_close_already_closed_returns_409(client, auth_headers):
    bug = _create_bug(client, auth_headers)
    client.post(
        f"/bugs/{bug['id']}/close",
        json={"resolution": "fixed", "annotation": "x"},
        headers=auth_headers,
    )
    resp = client.post(
        f"/bugs/{bug['id']}/close",
        json={"resolution": "fixed"},
        headers=auth_headers,
    )
    assert resp.status_code == 409


def test_reopen_bug(client, auth_headers):
    bug = _create_bug(client, auth_headers)
    client.post(
        f"/bugs/{bug['id']}/close",
        json={"resolution": "fixed", "annotation": "x"},
        headers=auth_headers,
    )
    resp = client.post(f"/bugs/{bug['id']}/reopen", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "open"


def test_reopen_open_bug_returns_409(client, auth_headers):
    bug = _create_bug(client, auth_headers)
    resp = client.post(f"/bugs/{bug['id']}/reopen", headers=auth_headers)
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Annotations
# ---------------------------------------------------------------------------

def test_add_annotation_requires_body(client, auth_headers):
    bug = _create_bug(client, auth_headers)
    resp = client.post(
        f"/bugs/{bug['id']}/annotations", json={}, headers=auth_headers,
    )
    assert resp.status_code == 400


def test_add_annotation_404(client, auth_headers):
    resp = client.post(
        "/bugs/BUG-9999/annotations",
        json={"body": "hi"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_add_annotation_happy_path(client, auth_headers):
    bug = _create_bug(client, auth_headers)
    resp = client.post(
        f"/bugs/{bug['id']}/annotations",
        json={"body": "First comment"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.get_json()["body"] == "First comment"


# ---------------------------------------------------------------------------
# Artifacts
# ---------------------------------------------------------------------------

def test_upload_artifact_requires_file(client, auth_headers):
    bug = _create_bug(client, auth_headers)
    resp = client.post(
        f"/bugs/{bug['id']}/artifacts",
        data={},
        headers=auth_headers,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400


def test_upload_and_download_artifact(client, auth_headers):
    bug = _create_bug(client, auth_headers)
    resp = client.post(
        f"/bugs/{bug['id']}/artifacts",
        data={"file": (io.BytesIO(b"hello world"), "notes.txt")},
        headers=auth_headers,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 201
    art = resp.get_json()
    assert art["filename"] == "notes.txt"

    download = client.get(
        f"/bugs/{bug['id']}/artifacts/{art['id']}", headers=auth_headers,
    )
    assert download.status_code == 200
    assert download.data == b"hello world"


def test_download_artifact_404(client, auth_headers):
    bug = _create_bug(client, auth_headers)
    resp = client.get(f"/bugs/{bug['id']}/artifacts/9999", headers=auth_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Relations
# ---------------------------------------------------------------------------

def test_add_and_remove_relation(client, auth_headers):
    a = _create_bug(client, auth_headers, title="a")
    b = _create_bug(client, auth_headers, title="b")

    add = client.post(
        f"/bugs/{a['id']}/relations",
        json={"related_id": b["id"]},
        headers=auth_headers,
    )
    assert add.status_code == 201
    # The relation should appear in the detailed bug view.
    detail = client.get(f"/bugs/{a['id']}", headers=auth_headers).get_json()
    assert b["id"] in detail["related_bugs"]

    rm = client.delete(
        f"/bugs/{a['id']}/relations/{b['id']}", headers=auth_headers,
    )
    assert rm.status_code == 204


def test_add_relation_requires_related_id(client, auth_headers):
    bug = _create_bug(client, auth_headers)
    resp = client.post(
        f"/bugs/{bug['id']}/relations", json={}, headers=auth_headers,
    )
    assert resp.status_code == 400


def test_add_relation_to_missing_target_returns_404(client, auth_headers):
    bug = _create_bug(client, auth_headers)
    resp = client.post(
        f"/bugs/{bug['id']}/relations",
        json={"related_id": "BUG-9999"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_add_relation_to_self_returns_400(client, auth_headers):
    bug = _create_bug(client, auth_headers)
    resp = client.post(
        f"/bugs/{bug['id']}/relations",
        json={"related_id": bug["id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_remove_missing_relation_returns_404(client, auth_headers):
    a = _create_bug(client, auth_headers, title="a")
    b = _create_bug(client, auth_headers, title="b")
    resp = client.delete(
        f"/bugs/{a['id']}/relations/{b['id']}", headers=auth_headers,
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Lookup-table APIs (products / areas / severities / platforms)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "prefix, field",
    [
        ("/api/products", "product"),
        ("/api/areas", "area"),
        ("/api/severities", "severity"),
        ("/api/platforms", "platform"),
    ],
)
def test_lookup_api_crud_cycle(client, auth_headers, prefix, field):
    # Create
    resp = client.post(
        prefix, json={"name": "Alpha", "description": "d"}, headers=auth_headers,
    )
    assert resp.status_code == 201

    # List (the new name should be visible)
    listed = client.get(prefix, headers=auth_headers).get_json()
    assert any(e["name"] == "Alpha" for e in listed)

    # Missing name
    resp = client.post(prefix, json={}, headers=auth_headers)
    assert resp.status_code == 400

    # Rename
    resp = client.patch(
        f"{prefix}/Alpha", json={"name": "Beta"}, headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.get_json()["name"] == "Beta"

    # Archive
    resp = client.patch(
        f"{prefix}/Beta", json={"archived": True}, headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.get_json()["archived"] is True

    # Archived rows are hidden by default but appear with include_archived.
    default = client.get(prefix, headers=auth_headers).get_json()
    assert not any(e["name"] == "Beta" for e in default)
    all_entries = client.get(
        f"{prefix}?include_archived=true", headers=auth_headers,
    ).get_json()
    assert any(e["name"] == "Beta" for e in all_entries)

    # Patching unknown name returns 404
    resp = client.patch(
        f"{prefix}/missing", json={"archived": True}, headers=auth_headers,
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

def test_404_json_handler(client):
    resp = client.get("/no-such-route")
    assert resp.status_code == 404
    assert resp.get_json() == {"error": "Not found"}


def test_405_json_handler(client, auth_headers):
    # GET /agents/<key> is not defined (only DELETE).
    resp = client.get("/agents/some-key", headers=auth_headers)
    assert resp.status_code == 405
    assert resp.get_json() == {"error": "Method not allowed"}
