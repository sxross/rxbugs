"""API integration tests — error handlers."""

from __future__ import annotations


def test_404_json_handler(client):
    resp = client.get("/no-such-route")
    assert resp.status_code == 404
    assert resp.get_json() == {"error": "Not found"}


def test_405_json_handler(client, auth_headers):
    # GET /agents/<key> is not defined (only DELETE).
    resp = client.get("/agents/some-key", headers=auth_headers)
    assert resp.status_code == 405
    assert resp.get_json() == {"error": "Method not allowed"}
