"""API integration tests — close / reopen."""

from __future__ import annotations

from tests.api_helpers import create_bug


def test_close_requires_resolution(client, auth_headers):
    bug = create_bug(client, auth_headers)
    resp = client.post(f"/bugs/{bug['id']}/close", json={}, headers=auth_headers)
    assert resp.status_code == 400


def test_close_bug_happy_path(client, auth_headers):
    bug = create_bug(client, auth_headers)
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
    bug = create_bug(client, auth_headers)
    resp = client.post(
        f"/bugs/{bug['id']}/close",
        json={"resolution": "fixed"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert "warnings" in resp.get_json()


def test_close_duplicate_without_link_warns(client, auth_headers):
    bug = create_bug(client, auth_headers)
    resp = client.post(
        f"/bugs/{bug['id']}/close",
        json={"resolution": "duplicate"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert any("duplicate" in w for w in resp.get_json()["warnings"])


def test_close_already_closed_returns_409(client, auth_headers):
    bug = create_bug(client, auth_headers)
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
    bug = create_bug(client, auth_headers)
    client.post(
        f"/bugs/{bug['id']}/close",
        json={"resolution": "fixed", "annotation": "x"},
        headers=auth_headers,
    )
    resp = client.post(f"/bugs/{bug['id']}/reopen", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "open"


def test_reopen_open_bug_returns_409(client, auth_headers):
    bug = create_bug(client, auth_headers)
    resp = client.post(f"/bugs/{bug['id']}/reopen", headers=auth_headers)
    assert resp.status_code == 409
