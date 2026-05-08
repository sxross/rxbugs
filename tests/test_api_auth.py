"""API integration tests — authentication & SPA shell."""

from __future__ import annotations


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
