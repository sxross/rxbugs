"""API integration tests — bug relations."""

from __future__ import annotations

from tests.api_helpers import create_bug


def test_add_and_remove_relation(client, auth_headers):
    a = create_bug(client, auth_headers, title="a")
    b = create_bug(client, auth_headers, title="b")

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
    bug = create_bug(client, auth_headers)
    resp = client.post(
        f"/bugs/{bug['id']}/relations", json={}, headers=auth_headers,
    )
    assert resp.status_code == 400


def test_add_relation_to_missing_target_returns_404(client, auth_headers):
    bug = create_bug(client, auth_headers)
    resp = client.post(
        f"/bugs/{bug['id']}/relations",
        json={"related_id": "BUG-9999"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_add_relation_to_self_returns_400(client, auth_headers):
    bug = create_bug(client, auth_headers)
    resp = client.post(
        f"/bugs/{bug['id']}/relations",
        json={"related_id": bug["id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_remove_missing_relation_returns_404(client, auth_headers):
    a = create_bug(client, auth_headers, title="a")
    b = create_bug(client, auth_headers, title="b")
    resp = client.delete(
        f"/bugs/{a['id']}/relations/{b['id']}", headers=auth_headers,
    )
    assert resp.status_code == 404
