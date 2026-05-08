"""API integration tests — annotations."""

from __future__ import annotations

from tests.api_helpers import create_bug


def test_add_annotation_requires_body(client, auth_headers):
    bug = create_bug(client, auth_headers)
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
    bug = create_bug(client, auth_headers)
    resp = client.post(
        f"/bugs/{bug['id']}/annotations",
        json={"body": "First comment"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.get_json()["body"] == "First comment"
