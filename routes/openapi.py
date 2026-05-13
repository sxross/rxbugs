"""Self-describing OpenAPI 3.0 spec endpoint."""

from flask import Blueprint, jsonify

openapi_bp = Blueprint("openapi", __name__)

_SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "RxBugs",
        "version": "1.0.0",
        "description": (
            "Lightweight self-hosted bug tracker REST API. "
            "Authenticate with a Bearer token in the Authorization header. "
            "Obtain a token from the server operator or via the QR-code login flow."
        ),
    },
    "servers": [{"url": "/", "description": "This server"}],
    "security": [{"bearerAuth": []}],
    "components": {
        "securitySchemes": {
            "bearerAuth": {"type": "http", "scheme": "bearer"},
        },
        "schemas": {
            "BugSummary": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "product": {"type": "string"},
                    "title": {"type": "string"},
                    "status": {"type": "string", "enum": ["open", "closed"]},
                    "resolution": {
                        "type": "string",
                        "enum": ["fixed", "duplicate", "no_repro", "wont_fix"],
                        "nullable": True,
                    },
                    "priority": {"type": "integer", "minimum": 1, "maximum": 5, "nullable": True},
                    "severity": {"type": "string", "nullable": True},
                    "area": {"type": "string", "nullable": True},
                    "platform": {"type": "string", "nullable": True},
                    "created_at": {"type": "string", "format": "date-time"},
                    "updated_at": {"type": "string", "format": "date-time"},
                },
            },
            "Bug": {
                "allOf": [
                    {"$ref": "#/components/schemas/BugSummary"},
                    {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string", "nullable": True},
                            "annotations": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/Annotation"},
                            },
                            "artifacts": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/Artifact"},
                            },
                            "related_bugs": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/BugSummary"},
                            },
                        },
                    },
                ],
            },
            "BugList": {
                "type": "object",
                "properties": {
                    "bugs": {"type": "array", "items": {"$ref": "#/components/schemas/BugSummary"}},
                    "total": {"type": "integer"},
                    "page": {"type": "integer"},
                    "per_page": {"type": "integer"},
                },
            },
            "Annotation": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "bug_id": {"type": "string"},
                    "body": {"type": "string"},
                    "author": {"type": "string"},
                    "author_type": {"type": "string"},
                    "created_at": {"type": "string", "format": "date-time"},
                },
            },
            "Artifact": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "bug_id": {"type": "string"},
                    "filename": {"type": "string"},
                    "mime_type": {"type": "string"},
                    "url": {"type": "string"},
                    "created_at": {"type": "string", "format": "date-time"},
                },
            },
            "LookupItem": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string", "nullable": True},
                    "archived": {"type": "boolean"},
                },
            },
            "Agent": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string", "nullable": True},
                    "key_prefix": {"type": "string"},
                    "rate_limit": {"type": "integer"},
                    "created_at": {"type": "string", "format": "date-time"},
                },
            },
            "Error": {
                "type": "object",
                "properties": {"error": {"type": "string"}},
            },
        },
    },
    "paths": {
        # -----------------------------------------------------------------
        # Bugs
        # -----------------------------------------------------------------
        "/bugs": {
            "get": {
                "summary": "List bugs",
                "operationId": "listBugs",
                "tags": ["bugs"],
                "parameters": [
                    {"name": "q", "in": "query", "schema": {"type": "string"}, "description": "Full-text search"},
                    {"name": "status", "in": "query", "schema": {"type": "string", "enum": ["open", "closed"]}},
                    {"name": "product", "in": "query", "schema": {"type": "array", "items": {"type": "string"}}, "style": "form", "explode": True},
                    {"name": "area", "in": "query", "schema": {"type": "array", "items": {"type": "string"}}, "style": "form", "explode": True},
                    {"name": "platform", "in": "query", "schema": {"type": "array", "items": {"type": "string"}}, "style": "form", "explode": True},
                    {"name": "severity", "in": "query", "schema": {"type": "array", "items": {"type": "string"}}, "style": "form", "explode": True},
                    {"name": "priority", "in": "query", "schema": {"type": "array", "items": {"type": "integer"}}, "style": "form", "explode": True},
                    {"name": "resolution", "in": "query", "schema": {"type": "array", "items": {"type": "string"}}, "style": "form", "explode": True},
                    {"name": "related_to", "in": "query", "schema": {"type": "string"}, "description": "Bug ID"},
                    {"name": "has_artifacts", "in": "query", "schema": {"type": "boolean"}},
                    {"name": "created_after", "in": "query", "schema": {"type": "string", "format": "date-time"}},
                    {"name": "created_before", "in": "query", "schema": {"type": "string", "format": "date-time"}},
                    {"name": "page", "in": "query", "schema": {"type": "integer", "default": 1}},
                    {"name": "per_page", "in": "query", "schema": {"type": "integer", "default": 25}},
                ],
                "responses": {
                    "200": {
                        "description": "Paginated bug list",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/BugList"}}},
                    },
                },
            },
            "post": {
                "summary": "Create a bug",
                "operationId": "createBug",
                "tags": ["bugs"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["product", "title"],
                                "properties": {
                                    "product": {"type": "string"},
                                    "title": {"type": "string"},
                                    "description": {"type": "string"},
                                    "area": {"type": "string"},
                                    "platform": {"type": "string"},
                                    "priority": {"type": "integer", "minimum": 1, "maximum": 5},
                                    "severity": {"type": "string"},
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "201": {
                        "description": "Created bug",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Bug"}}},
                    },
                    "400": {"description": "Validation error", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                },
            },
        },
        "/bugs/{bug_id}": {
            "parameters": [{"name": "bug_id", "in": "path", "required": True, "schema": {"type": "string"}}],
            "get": {
                "summary": "Get bug detail",
                "operationId": "getBug",
                "tags": ["bugs"],
                "responses": {
                    "200": {
                        "description": "Bug with annotations, artifacts, and related bugs",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Bug"}}},
                    },
                    "404": {"description": "Not found", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                },
            },
            "patch": {
                "summary": "Update a bug",
                "operationId": "updateBug",
                "tags": ["bugs"],
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "description": {"type": "string"},
                                    "area": {"type": "string"},
                                    "platform": {"type": "string"},
                                    "priority": {"type": "integer", "minimum": 1, "maximum": 5},
                                    "severity": {"type": "string"},
                                },
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Updated bug",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/BugSummary"}}},
                    },
                    "404": {"description": "Not found", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                },
            },
        },
        "/bugs/{bug_id}/close": {
            "parameters": [{"name": "bug_id", "in": "path", "required": True, "schema": {"type": "string"}}],
            "post": {
                "summary": "Close a bug",
                "operationId": "closeBug",
                "tags": ["bugs"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["resolution"],
                                "properties": {
                                    "resolution": {"type": "string", "enum": ["fixed", "duplicate", "no_repro", "wont_fix"]},
                                    "annotation": {"type": "string", "description": "Optional closing note"},
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "200": {"description": "Closed bug", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/BugSummary"}}}},
                    "404": {"description": "Not found", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                    "409": {"description": "Already closed", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                },
            },
        },
        "/bugs/{bug_id}/reopen": {
            "parameters": [{"name": "bug_id", "in": "path", "required": True, "schema": {"type": "string"}}],
            "post": {
                "summary": "Reopen a closed bug",
                "operationId": "reopenBug",
                "tags": ["bugs"],
                "responses": {
                    "200": {"description": "Reopened bug", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/BugSummary"}}}},
                    "404": {"description": "Not found", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                    "409": {"description": "Already open", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                },
            },
        },
        "/bugs/{bug_id}/annotations": {
            "parameters": [{"name": "bug_id", "in": "path", "required": True, "schema": {"type": "string"}}],
            "post": {
                "summary": "Add an annotation to a bug",
                "operationId": "addAnnotation",
                "tags": ["annotations"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["body"],
                                "properties": {"body": {"type": "string"}},
                            }
                        }
                    },
                },
                "responses": {
                    "201": {"description": "Created annotation", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Annotation"}}}},
                    "404": {"description": "Bug not found", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                },
            },
        },
        "/bugs/{bug_id}/relations": {
            "parameters": [{"name": "bug_id", "in": "path", "required": True, "schema": {"type": "string"}}],
            "post": {
                "summary": "Link a related bug",
                "operationId": "addRelation",
                "tags": ["relations"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["related_id"],
                                "properties": {"related_id": {"type": "string"}},
                            }
                        }
                    },
                },
                "responses": {
                    "201": {"description": "Relation created"},
                    "404": {"description": "Bug not found", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                },
            },
        },
        "/bugs/{bug_id}/relations/{related_id}": {
            "parameters": [
                {"name": "bug_id", "in": "path", "required": True, "schema": {"type": "string"}},
                {"name": "related_id", "in": "path", "required": True, "schema": {"type": "string"}},
            ],
            "delete": {
                "summary": "Remove a relation between two bugs",
                "operationId": "removeRelation",
                "tags": ["relations"],
                "responses": {
                    "204": {"description": "Relation removed"},
                    "404": {"description": "Relation not found", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                },
            },
        },
        "/bugs/{bug_id}/artifacts": {
            "parameters": [{"name": "bug_id", "in": "path", "required": True, "schema": {"type": "string"}}],
            "post": {
                "summary": "Upload a file artifact",
                "operationId": "uploadArtifact",
                "tags": ["artifacts"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "multipart/form-data": {
                            "schema": {
                                "type": "object",
                                "required": ["file"],
                                "properties": {"file": {"type": "string", "format": "binary"}},
                            }
                        }
                    },
                },
                "responses": {
                    "201": {"description": "Uploaded artifact", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Artifact"}}}},
                    "400": {"description": "File type not allowed", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                },
            },
        },
        "/bugs/{bug_id}/artifacts/{artifact_id}": {
            "parameters": [
                {"name": "bug_id", "in": "path", "required": True, "schema": {"type": "string"}},
                {"name": "artifact_id", "in": "path", "required": True, "schema": {"type": "integer"}},
            ],
            "get": {
                "summary": "Download an artifact",
                "operationId": "downloadArtifact",
                "tags": ["artifacts"],
                "responses": {
                    "200": {"description": "File download"},
                    "404": {"description": "Not found", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                },
            },
        },
        # -----------------------------------------------------------------
        # Auth
        # -----------------------------------------------------------------
        "/auth/session": {
            "post": {
                "summary": "Create a short-lived session token for QR login",
                "operationId": "createSession",
                "tags": ["auth"],
                "responses": {
                    "200": {
                        "description": "Session token (expires in 300 s)",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "session_token": {"type": "string"},
                                        "expires_in": {"type": "integer"},
                                    },
                                }
                            }
                        },
                    },
                },
            },
        },
        "/auth/qr": {
            "get": {
                "summary": "Get a QR code PNG encoding a one-time login URL",
                "operationId": "getQrCode",
                "tags": ["auth"],
                "responses": {
                    "200": {"description": "PNG image", "content": {"image/png": {}}},
                },
            },
        },
        "/auth/login": {
            "get": {
                "summary": "Validate a session token and return an authenticated page",
                "operationId": "sessionLogin",
                "tags": ["auth"],
                "security": [],
                "parameters": [
                    {"name": "session", "in": "query", "required": True, "schema": {"type": "string"}},
                ],
                "responses": {
                    "200": {"description": "HTML page that stores the token in localStorage"},
                    "403": {"description": "Invalid or expired session token"},
                },
            },
        },
        # -----------------------------------------------------------------
        # Admin — agents
        # -----------------------------------------------------------------
        "/agents": {
            "get": {
                "summary": "List agent keys",
                "operationId": "listAgents",
                "tags": ["admin"],
                "responses": {
                    "200": {
                        "description": "List of agents",
                        "content": {"application/json": {"schema": {"type": "array", "items": {"$ref": "#/components/schemas/Agent"}}}},
                    },
                },
            },
            "post": {
                "summary": "Register a new agent key",
                "operationId": "registerAgent",
                "tags": ["admin"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["name"],
                                "properties": {
                                    "name": {"type": "string"},
                                    "description": {"type": "string"},
                                    "rate_limit": {"type": "integer", "default": 60, "description": "Requests per minute"},
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "201": {
                        "description": "Agent with raw key (only returned once)",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "allOf": [
                                        {"$ref": "#/components/schemas/Agent"},
                                        {"type": "object", "properties": {"key": {"type": "string"}}},
                                    ]
                                }
                            }
                        },
                    },
                },
            },
        },
        "/agents/{key}": {
            "parameters": [{"name": "key", "in": "path", "required": True, "schema": {"type": "string"}}],
            "delete": {
                "summary": "Revoke an agent key",
                "operationId": "revokeAgent",
                "tags": ["admin"],
                "responses": {
                    "204": {"description": "Revoked"},
                    "404": {"description": "Not found", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                },
            },
        },
        # -----------------------------------------------------------------
        # Admin — lookup tables (products / areas / severities / platforms)
        # -----------------------------------------------------------------
        "/api/products": {
            "get": {
                "summary": "List products",
                "operationId": "listProducts",
                "tags": ["admin"],
                "parameters": [{"name": "include_archived", "in": "query", "schema": {"type": "boolean"}}],
                "responses": {"200": {"description": "Products", "content": {"application/json": {"schema": {"type": "array", "items": {"$ref": "#/components/schemas/LookupItem"}}}}}},
            },
            "post": {
                "summary": "Create a product",
                "operationId": "createProduct",
                "tags": ["admin"],
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}, "description": {"type": "string"}}}}}},
                "responses": {"201": {"description": "Created product", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/LookupItem"}}}}},
            },
        },
        "/api/products/{name}": {
            "parameters": [{"name": "name", "in": "path", "required": True, "schema": {"type": "string"}}],
            "patch": {
                "summary": "Rename or archive a product",
                "operationId": "updateProduct",
                "tags": ["admin"],
                "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"name": {"type": "string"}, "archived": {"type": "boolean"}}}}}},
                "responses": {"200": {"description": "Updated product", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/LookupItem"}}}}},
            },
        },
        "/api/areas": {
            "get": {"summary": "List areas", "operationId": "listAreas", "tags": ["admin"], "parameters": [{"name": "include_archived", "in": "query", "schema": {"type": "boolean"}}], "responses": {"200": {"description": "Areas", "content": {"application/json": {"schema": {"type": "array", "items": {"$ref": "#/components/schemas/LookupItem"}}}}}}},
            "post": {"summary": "Create an area", "operationId": "createArea", "tags": ["admin"], "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}, "description": {"type": "string"}}}}}}, "responses": {"201": {"description": "Created area", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/LookupItem"}}}}}},
        },
        "/api/areas/{name}": {
            "parameters": [{"name": "name", "in": "path", "required": True, "schema": {"type": "string"}}],
            "patch": {"summary": "Rename or archive an area", "operationId": "updateArea", "tags": ["admin"], "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"name": {"type": "string"}, "archived": {"type": "boolean"}}}}}}, "responses": {"200": {"description": "Updated area", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/LookupItem"}}}}}},
        },
        "/api/severities": {
            "get": {"summary": "List severities", "operationId": "listSeverities", "tags": ["admin"], "parameters": [{"name": "include_archived", "in": "query", "schema": {"type": "boolean"}}], "responses": {"200": {"description": "Severities", "content": {"application/json": {"schema": {"type": "array", "items": {"$ref": "#/components/schemas/LookupItem"}}}}}}},
            "post": {"summary": "Create a severity", "operationId": "createSeverity", "tags": ["admin"], "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}, "description": {"type": "string"}}}}}}, "responses": {"201": {"description": "Created severity", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/LookupItem"}}}}}},
        },
        "/api/severities/{name}": {
            "parameters": [{"name": "name", "in": "path", "required": True, "schema": {"type": "string"}}],
            "patch": {"summary": "Rename or archive a severity", "operationId": "updateSeverity", "tags": ["admin"], "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"name": {"type": "string"}, "archived": {"type": "boolean"}}}}}}, "responses": {"200": {"description": "Updated severity", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/LookupItem"}}}}}},
        },
        "/api/platforms": {
            "get": {"summary": "List platforms", "operationId": "listPlatforms", "tags": ["admin"], "parameters": [{"name": "include_archived", "in": "query", "schema": {"type": "boolean"}}], "responses": {"200": {"description": "Platforms", "content": {"application/json": {"schema": {"type": "array", "items": {"$ref": "#/components/schemas/LookupItem"}}}}}}},
            "post": {"summary": "Create a platform", "operationId": "createPlatform", "tags": ["admin"], "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}, "description": {"type": "string"}}}}}}, "responses": {"201": {"description": "Created platform", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/LookupItem"}}}}}},
        },
        "/api/platforms/{name}": {
            "parameters": [{"name": "name", "in": "path", "required": True, "schema": {"type": "string"}}],
            "patch": {"summary": "Rename or archive a platform", "operationId": "updatePlatform", "tags": ["admin"], "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"name": {"type": "string"}, "archived": {"type": "boolean"}}}}}}, "responses": {"200": {"description": "Updated platform", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/LookupItem"}}}}}},
        },
    },
    "tags": [
        {"name": "bugs", "description": "Bug CRUD and lifecycle (close, reopen)"},
        {"name": "annotations", "description": "Text notes attached to a bug"},
        {"name": "artifacts", "description": "File uploads attached to a bug"},
        {"name": "relations", "description": "Links between related bugs"},
        {"name": "auth", "description": "QR-code / session-token login flow"},
        {"name": "admin", "description": "Lookup tables (products, areas, severities, platforms) and agent keys"},
    ],
}


@openapi_bp.route("/api", methods=["GET"])
def openapi_spec():
    """Return the OpenAPI 3.0 spec. No authentication required."""
    return jsonify(_SPEC)
