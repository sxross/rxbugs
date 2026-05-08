"""API integration tests — bug create / list / get / update."""

from __future__ import annotations

import io

from tests.api_helpers import create_bug


def test_create_bug_requires_product(client, auth_headers):
    resp = client.post("/bugs", json={"title": "t"}, headers=auth_headers)
    assert resp.status_code == 400
    assert "product" in resp.get_json()["error"]


def test_create_bug_requires_title(client, auth_headers):
    resp = client.post("/bugs", json={"product": "p"}, headers=auth_headers)
    assert resp.status_code == 400
    assert "title" in resp.get_json()["error"]


def test_create_bug_happy_path(client, auth_headers):
    bug = create_bug(client, auth_headers, priority=1, severity="showstopper")
    assert bug["id"].startswith("BUG-")
    assert bug["status"] == "open"
    assert bug["priority"] == 1
    assert bug["severity"] == "showstopper"


def test_list_bugs_returns_total_and_list(client, auth_headers):
    create_bug(client, auth_headers, title="first")
    create_bug(client, auth_headers, title="second")
    resp = client.get("/bugs", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] == 2
    assert len(data["bugs"]) == 2


def test_list_bugs_with_priority_filter(client, auth_headers):
    create_bug(client, auth_headers, title="p1", priority=1)
    create_bug(client, auth_headers, title="p2", priority=2)
    resp = client.get("/bugs?priority=1", headers=auth_headers)
    assert resp.status_code == 200
    titles = [b["title"] for b in resp.get_json()["bugs"]]
    assert titles == ["p1"]


def test_list_bugs_invalid_priority(client, auth_headers):
    resp = client.get("/bugs?priority=notanumber", headers=auth_headers)
    assert resp.status_code == 400


def test_list_bugs_multi_valued_filter(client, auth_headers):
    create_bug(client, auth_headers, title="a", area="ui")
    create_bug(client, auth_headers, title="b", area="backend")
    create_bug(client, auth_headers, title="c", area="sync")
    resp = client.get("/bugs?area=ui&area=backend", headers=auth_headers)
    titles = {b["title"] for b in resp.get_json()["bugs"]}
    assert titles == {"a", "b"}


def test_list_bugs_has_artifacts_filter(client, auth_headers):
    with_art = create_bug(client, auth_headers, title="with")
    create_bug(client, auth_headers, title="without")
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
    bug = create_bug(client, auth_headers)
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
    bug = create_bug(client, auth_headers, title="old")
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
