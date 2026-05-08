"""API integration tests — lookup-table APIs (products/areas/severities/platforms)."""

from __future__ import annotations

import pytest


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
