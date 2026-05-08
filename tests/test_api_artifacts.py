"""API integration tests — artifacts."""

from __future__ import annotations

import io

from tests.api_helpers import create_bug


def test_upload_artifact_requires_file(client, auth_headers):
    bug = create_bug(client, auth_headers)
    resp = client.post(
        f"/bugs/{bug['id']}/artifacts",
        data={},
        headers=auth_headers,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400


def test_upload_and_download_artifact(client, auth_headers):
    bug = create_bug(client, auth_headers)
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
    bug = create_bug(client, auth_headers)
    resp = client.get(f"/bugs/{bug['id']}/artifacts/9999", headers=auth_headers)
    assert resp.status_code == 404
