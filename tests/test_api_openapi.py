"""Tests for the self-describing GET /api endpoint."""

import pytest


def test_openapi_no_auth_required(client):
    """GET /api is publicly accessible — no Authorization header needed."""
    resp = client.get("/api")
    assert resp.status_code == 200


def test_openapi_returns_json(client):
    resp = client.get("/api")
    assert resp.content_type.startswith("application/json")


def test_openapi_top_level_structure(client):
    data = client.get("/api").get_json()
    assert data["openapi"].startswith("3.")
    assert "info" in data
    assert "paths" in data
    assert "components" in data
    assert "tags" in data


def test_openapi_info_fields(client):
    info = client.get("/api").get_json()["info"]
    assert info["title"] == "RxBugs"
    assert "version" in info
    assert "description" in info


def test_openapi_security_scheme_defined(client):
    schemes = client.get("/api").get_json()["components"]["securitySchemes"]
    assert "bearerAuth" in schemes
    assert schemes["bearerAuth"]["type"] == "http"
    assert schemes["bearerAuth"]["scheme"] == "bearer"


def test_openapi_global_security_requires_bearer(client):
    security = client.get("/api").get_json()["security"]
    assert {"bearerAuth": []} in security


def test_openapi_bugs_paths_present(client):
    paths = client.get("/api").get_json()["paths"]
    assert "/bugs" in paths
    assert "/bugs/{bug_id}" in paths
    assert "/bugs/{bug_id}/close" in paths
    assert "/bugs/{bug_id}/reopen" in paths
    assert "/bugs/{bug_id}/annotations" in paths
    assert "/bugs/{bug_id}/relations" in paths
    assert "/bugs/{bug_id}/relations/{related_id}" in paths
    assert "/bugs/{bug_id}/artifacts" in paths
    assert "/bugs/{bug_id}/artifacts/{artifact_id}" in paths


def test_openapi_admin_paths_present(client):
    paths = client.get("/api").get_json()["paths"]
    assert "/agents" in paths
    assert "/agents/{key}" in paths
    for resource in ("products", "areas", "severities", "platforms"):
        assert f"/api/{resource}" in paths
        assert f"/api/{resource}/{{name}}" in paths


def test_openapi_auth_paths_present(client):
    paths = client.get("/api").get_json()["paths"]
    assert "/auth/session" in paths
    assert "/auth/qr" in paths
    assert "/auth/login" in paths


def test_openapi_bugs_list_methods(client):
    bugs = client.get("/api").get_json()["paths"]["/bugs"]
    assert "get" in bugs
    assert "post" in bugs


def test_openapi_bugs_list_get_has_filters(client):
    params = client.get("/api").get_json()["paths"]["/bugs"]["get"]["parameters"]
    param_names = [p["name"] for p in params]
    for expected in ("q", "status", "product", "area", "platform", "severity", "priority", "page", "per_page"):
        assert expected in param_names, f"missing filter param: {expected}"


def test_openapi_create_bug_required_fields(client):
    post = client.get("/api").get_json()["paths"]["/bugs"]["post"]
    schema = post["requestBody"]["content"]["application/json"]["schema"]
    assert "product" in schema["required"]
    assert "title" in schema["required"]


def test_openapi_close_bug_resolution_enum(client):
    post = client.get("/api").get_json()["paths"]["/bugs/{bug_id}/close"]["post"]
    schema = post["requestBody"]["content"]["application/json"]["schema"]
    resolution = next(p for name, p in schema["properties"].items() if name == "resolution")
    assert set(resolution["enum"]) == {"fixed", "duplicate", "no_repro", "wont_fix"}


def test_openapi_schemas_defined(client):
    schemas = client.get("/api").get_json()["components"]["schemas"]
    for name in ("Bug", "BugSummary", "BugList", "Annotation", "Artifact", "LookupItem", "Agent", "Error"):
        assert name in schemas, f"missing schema: {name}"


def test_openapi_bug_summary_has_key_properties(client):
    props = client.get("/api").get_json()["components"]["schemas"]["BugSummary"]["properties"]
    for field in ("id", "product", "title", "status", "resolution", "priority", "severity", "created_at"):
        assert field in props, f"missing BugSummary property: {field}"


def test_openapi_auth_login_is_unauthenticated(client):
    """The /auth/login endpoint overrides global security with an empty list."""
    login = client.get("/api").get_json()["paths"]["/auth/login"]["get"]
    assert login.get("security") == []


def test_openapi_register_agent_requires_name(client):
    post = client.get("/api").get_json()["paths"]["/agents"]["post"]
    schema = post["requestBody"]["content"]["application/json"]["schema"]
    assert "name" in schema["required"]


def test_openapi_tags_cover_main_groups(client):
    tag_names = {t["name"] for t in client.get("/api").get_json()["tags"]}
    for expected in ("bugs", "annotations", "artifacts", "relations", "auth", "admin"):
        assert expected in tag_names, f"missing tag: {expected}"


def test_openapi_operation_ids_unique(client):
    paths = client.get("/api").get_json()["paths"]
    ids = []
    for path_item in paths.values():
        for method_obj in path_item.values():
            if isinstance(method_obj, dict) and "operationId" in method_obj:
                ids.append(method_obj["operationId"])
    assert len(ids) == len(set(ids)), "duplicate operationIds found"


def test_openapi_upload_artifact_uses_multipart(client):
    post = client.get("/api").get_json()["paths"]["/bugs/{bug_id}/artifacts"]["post"]
    assert "multipart/form-data" in post["requestBody"]["content"]


def test_openapi_spec_is_stable(client):
    """Two successive calls return identical content (no random generation)."""
    a = client.get("/api").get_json()
    b = client.get("/api").get_json()
    assert a == b
