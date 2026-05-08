"""Shared helpers for API integration tests."""

from __future__ import annotations


def create_bug(client, headers, **overrides):
    """Create a bug via the API and return the JSON response."""
    payload = {"product": "RxTrack", "title": "A bug"}
    payload.update(overrides)
    resp = client.post("/bugs", json=payload, headers=headers)
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()
