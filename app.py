"""RxBugs — Flask application entry point.

Starts the server, runs Alembic migrations on first launch,
and defines all API routes.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------

_TOKEN = os.environ.get("BUGTRACKER_TOKEN")
if not _TOKEN:
    print("ERROR: BUGTRACKER_TOKEN environment variable is not set.", file=sys.stderr)
    print("Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\"",
          file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Database + migrations
# ---------------------------------------------------------------------------

from db.connection import init_engine, make_search_backend

_engine = init_engine()
_search = make_search_backend(_engine)

# Run Alembic migrations on startup (idempotent — safe to run every time)
from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig

def _run_migrations() -> None:
    cfg = AlembicConfig(str(Path(__file__).parent / "alembic.ini"))
    cfg.set_main_option(
        "script_location", str(Path(__file__).parent / "alembic")
    )
    alembic_command.upgrade(cfg, "head")

_run_migrations()

# ---------------------------------------------------------------------------
# Flask app + rate limiter
# ---------------------------------------------------------------------------

from flask import Flask, g, jsonify, request, send_from_directory
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from auth import bad as _bad, init_auth, require_auth

# ---------------------------------------------------------------------------
# Named constants (review item P10)
# ---------------------------------------------------------------------------

MAX_UPLOAD_MB = 50
DEFAULT_RATE_LIMIT = "200 per minute"
QR_RATE_LIMIT = "20 per minute"
DEFAULT_AGENT_RATE_LIMIT = 60

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024

_UPLOADS_DIR = Path(__file__).parent / "uploads"
_UPLOADS_DIR.mkdir(exist_ok=True)

limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[DEFAULT_RATE_LIMIT],
    storage_uri="memory://",
)

init_auth(_TOKEN, _engine)


def _bug_or_404(bug_id: str):
    from db import bugs as bugs_repo
    bug = bugs_repo.get(_engine, bug_id)
    if bug is None:
        return None, _bad(f"Bug '{bug_id}' not found.", 404)
    return bug, None


# ---------------------------------------------------------------------------
# SPA shell
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


# ---------------------------------------------------------------------------
# Bugs — list / create
# ---------------------------------------------------------------------------

import db.agents as agents_repo
import db.annotations as annotations_repo
import db.areas as areas_repo
import db.artifacts as artifacts_repo
import db.bugs as bugs_repo
import db.platforms as platforms_repo
import db.products as products_repo
import db.relations as relations_repo
import db.severities as severities_repo


@app.route("/bugs", methods=["GET"])
@require_auth
def list_bugs():
    from db.types import BugFilters

    def _multi(key: str) -> list | None:
        vals = request.args.getlist(key)
        return vals if vals else None

    filters: BugFilters = {}
    if request.args.get("q"):
        filters["q"] = request.args["q"]
    if _multi("product"):
        filters["product"] = _multi("product")  # type: ignore[assignment]
    if _multi("area"):
        filters["area"] = _multi("area")  # type: ignore[assignment]
    if _multi("platform"):
        filters["platform"] = _multi("platform")  # type: ignore[assignment]
    if _multi("priority"):
        try:
            filters["priority"] = [int(p) for p in _multi("priority")]  # type: ignore[assignment]
        except ValueError:
            return _bad("priority must be an integer.")
    if _multi("severity"):
        filters["severity"] = _multi("severity")  # type: ignore[assignment]
    if request.args.get("status"):
        filters["status"] = request.args["status"]  # type: ignore[assignment]
    if _multi("resolution"):
        filters["resolution"] = _multi("resolution")  # type: ignore[assignment]
    if request.args.get("related_to"):
        filters["related_to"] = request.args["related_to"]
    if request.args.get("has_artifacts") is not None:
        filters["has_artifacts"] = request.args.get("has_artifacts", "").lower() == "true"
    if request.args.get("created_after"):
        filters["created_after"] = request.args["created_after"]
    if request.args.get("created_before"):
        filters["created_before"] = request.args["created_before"]

    results = _search.query(filters)
    return jsonify({"total": len(results), "bugs": results})


@app.route("/bugs", methods=["POST"])
@require_auth
def create_bug():
    data = request.get_json(silent=True) or {}
    if not data.get("product"):
        return _bad("product is required.")
    if not data.get("title"):
        return _bad("title is required.")

    bug = bugs_repo.create(
        _engine,
        product=data["product"],
        title=data["title"],
        description=data.get("description"),
        area=data.get("area"),
        platform=data.get("platform"),
        priority=data.get("priority"),
        severity=data.get("severity"),
        actor=g.actor,
        actor_type=g.actor_type,
    )
    return jsonify(bug), 201


# ---------------------------------------------------------------------------
# Bugs — single resource
# ---------------------------------------------------------------------------

@app.route("/bugs/<bug_id>", methods=["GET"])
@require_auth
def get_bug(bug_id: str):
    bug, err = _bug_or_404(bug_id)
    if err:
        return err
    annotations = annotations_repo.list_for_bug(_engine, bug_id)
    artifacts = artifacts_repo.list_for_bug(_engine, bug_id)
    related = relations_repo.list_for_bug(_engine, bug_id)
    return jsonify({
        **bug,
        "annotations": annotations,
        "artifacts": [
            {**a, "url": f"/bugs/{bug_id}/artifacts/{a['id']}"}
            for a in artifacts
        ],
        "related_bugs": related,
    })


@app.route("/bugs/<bug_id>", methods=["PATCH"])
@require_auth
def update_bug(bug_id: str):
    bug, err = _bug_or_404(bug_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    updated = bugs_repo.update(
        _engine, bug_id,
        actor=g.actor, actor_type=g.actor_type,
        **data,
    )
    return jsonify(updated)


# ---------------------------------------------------------------------------
# Close / Reopen
# ---------------------------------------------------------------------------

@app.route("/bugs/<bug_id>/close", methods=["POST"])
@require_auth
def close_bug(bug_id: str):
    bug, err = _bug_or_404(bug_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    resolution = data.get("resolution")
    if not resolution:
        return _bad("resolution is required when closing a bug.")

    # Agent warnings (non-blocking)
    warnings = []
    if resolution == "duplicate":
        related = relations_repo.list_for_bug(_engine, bug_id)
        if not related:
            warnings.append(
                "Closing as 'duplicate' without linking the canonical bug is not recommended."
            )
    if resolution == "fixed":
        existing = annotations_repo.list_for_bug(_engine, bug_id)
        if not existing and not data.get("annotation"):
            warnings.append(
                "Closing as 'fixed' without an annotation is not recommended."
            )

    try:
        updated = bugs_repo.close(
            _engine, bug_id,
            resolution=resolution,
            actor=g.actor, actor_type=g.actor_type,
        )
    except ValueError as exc:
        return _bad(str(exc), 409)

    if data.get("annotation"):
        annotations_repo.create(
            _engine,
            bug_id=bug_id,
            author=g.actor,
            author_type=g.actor_type,
            body=data["annotation"],
        )

    resp = {"bug": updated}
    if warnings:
        resp["warnings"] = warnings
    return jsonify(resp)


@app.route("/bugs/<bug_id>/reopen", methods=["POST"])
@require_auth
def reopen_bug(bug_id: str):
    bug, err = _bug_or_404(bug_id)
    if err:
        return err
    try:
        updated = bugs_repo.reopen(
            _engine, bug_id,
            actor=g.actor, actor_type=g.actor_type,
        )
    except ValueError as exc:
        return _bad(str(exc), 409)
    return jsonify(updated)


# ---------------------------------------------------------------------------
# Annotations
# ---------------------------------------------------------------------------

@app.route("/bugs/<bug_id>/annotations", methods=["POST"])
@require_auth
def add_annotation(bug_id: str):
    _, err = _bug_or_404(bug_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    if not data.get("body"):
        return _bad("body is required.")
    annotation = annotations_repo.create(
        _engine,
        bug_id=bug_id,
        author=g.actor,
        author_type=g.actor_type,
        body=data["body"],
    )
    return jsonify(annotation), 201


# ---------------------------------------------------------------------------
# Artifacts
# ---------------------------------------------------------------------------

@app.route("/bugs/<bug_id>/artifacts", methods=["POST"])
@require_auth
def upload_artifact(bug_id: str):
    _, err = _bug_or_404(bug_id)
    if err:
        return err
    if "file" not in request.files:
        return _bad("file is required.")

    file = request.files["file"]
    filename = file.filename or "upload"

    dest_dir = _UPLOADS_DIR / bug_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    # Avoid collisions by prepending a short random prefix
    import secrets as _secrets
    safe_name = _secrets.token_hex(4) + "_" + Path(filename).name
    dest_path = dest_dir / safe_name
    file.save(dest_path)

    relative_path = str(Path(bug_id) / safe_name)
    artifact = artifacts_repo.create(
        _engine,
        bug_id=bug_id,
        filename=filename,
        path=relative_path,
        mime_type=file.content_type,
        actor=g.actor,
        actor_type=g.actor_type,
    )
    return jsonify(artifact), 201


@app.route("/bugs/<bug_id>/artifacts/<int:artifact_id>", methods=["GET"])
@require_auth
def download_artifact(bug_id: str, artifact_id: int):
    artifact = artifacts_repo.get(_engine, artifact_id)
    if artifact is None or artifact["bug_id"] != bug_id:
        return _bad("Artifact not found.", 404)
    abs_path = _UPLOADS_DIR / artifact["path"]
    return send_from_directory(
        str(abs_path.parent),
        abs_path.name,
        as_attachment=True,
        download_name=artifact["filename"],
    )


# ---------------------------------------------------------------------------
# Relations
# ---------------------------------------------------------------------------

@app.route("/bugs/<bug_id>/relations", methods=["POST"])
@require_auth
def add_relation(bug_id: str):
    _, err = _bug_or_404(bug_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    related_id = data.get("related_id")
    if not related_id:
        return _bad("related_id is required.")
    related_bug, rel_err = _bug_or_404(related_id)
    if rel_err:
        return _bad(f"Related bug '{related_id}' not found.", 404)
    try:
        relations_repo.link(
            _engine, bug_id, related_id,
            actor=g.actor, actor_type=g.actor_type,
        )
    except ValueError as exc:
        return _bad(str(exc))
    return jsonify({"bug_id": bug_id, "related_id": related_id}), 201


@app.route("/bugs/<bug_id>/relations/<related_id>", methods=["DELETE"])
@require_auth
def remove_relation(bug_id: str, related_id: str):
    existed = relations_repo.unlink(
        _engine, bug_id, related_id,
        actor=g.actor, actor_type=g.actor_type,
    )
    if not existed:
        return _bad("Relation not found.", 404)
    return "", 204


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------

@app.route("/agents", methods=["GET"])
@require_auth
def list_agents():
    return jsonify(agents_repo.list_agents(_engine))


@app.route("/agents", methods=["POST"])
@require_auth
def register_agent():
    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return _bad("name is required.")
    agent, raw_key = agents_repo.register(
        _engine,
        name=data["name"],
        description=data.get("description"),
        rate_limit=int(data.get("rate_limit", DEFAULT_AGENT_RATE_LIMIT)),
    )
    # Return the raw key once — it is not retrievable after this response
    return jsonify({**agent, "key": raw_key}), 201


@app.route("/agents/<key>", methods=["DELETE"])
@require_auth
def revoke_agent(key: str):
    revoked = agents_repo.revoke(_engine, key)
    if not revoked:
        return _bad("Agent not found.", 404)
    return "", 204


# ---------------------------------------------------------------------------
# Products API
# ---------------------------------------------------------------------------

@app.route("/api/products", methods=["GET"])
@require_auth
def list_products_route():
    include_archived = request.args.get("include_archived", "").lower() == "true"
    return jsonify(products_repo.list_products(_engine, include_archived=include_archived))


@app.route("/api/products", methods=["POST"])
@require_auth
def create_product():
    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return _bad("name is required.")
    product = products_repo.create(
        _engine, name=data["name"], description=data.get("description")
    )
    return jsonify(product), 201


@app.route("/api/products/<name>", methods=["PATCH"])
@require_auth
def update_product(name: str):
    data = request.get_json(silent=True) or {}
    if "name" in data and data["name"] != name:
        result = products_repo.rename(_engine, name, data["name"])
    elif data.get("archived") is True:
        result = products_repo.archive(_engine, name)
    else:
        result = products_repo.get(_engine, name)
    if result is None:
        return _bad(f"Product '{name}' not found.", 404)
    return jsonify(result)


# ---------------------------------------------------------------------------
# Areas API
# ---------------------------------------------------------------------------

@app.route("/api/areas", methods=["GET"])
@require_auth
def list_areas_route():
    include_archived = request.args.get("include_archived", "").lower() == "true"
    return jsonify(areas_repo.list_areas(_engine, include_archived=include_archived))


@app.route("/api/areas", methods=["POST"])
@require_auth
def create_area():
    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return _bad("name is required.")
    area = areas_repo.create(
        _engine, name=data["name"], description=data.get("description")
    )
    return jsonify(area), 201


@app.route("/api/areas/<name>", methods=["PATCH"])
@require_auth
def update_area(name: str):
    data = request.get_json(silent=True) or {}
    if "name" in data and data["name"] != name:
        result = areas_repo.rename(_engine, name, data["name"])
    elif data.get("archived") is True:
        result = areas_repo.archive(_engine, name)
    else:
        result = areas_repo.get(_engine, name)
    if result is None:
        return _bad(f"Area '{name}' not found.", 404)
    return jsonify(result)


# ---------------------------------------------------------------------------
# Severities API
# ---------------------------------------------------------------------------

@app.route("/api/severities", methods=["GET"])
@require_auth
def list_severities_route():
    include_archived = request.args.get("include_archived", "").lower() == "true"
    return jsonify(
        severities_repo.list_severities(_engine, include_archived=include_archived)
    )


@app.route("/api/severities", methods=["POST"])
@require_auth
def create_severity():
    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return _bad("name is required.")
    severity = severities_repo.create(
        _engine, name=data["name"], description=data.get("description")
    )
    return jsonify(severity), 201


@app.route("/api/severities/<name>", methods=["PATCH"])
@require_auth
def update_severity(name: str):
    data = request.get_json(silent=True) or {}
    if "name" in data and data["name"] != name:
        result = severities_repo.rename(_engine, name, data["name"])
    elif data.get("archived") is True:
        result = severities_repo.archive(_engine, name)
    else:
        result = severities_repo.get(_engine, name)
    if result is None:
        return _bad(f"Severity '{name}' not found.", 404)
    return jsonify(result)


# ---------------------------------------------------------------------------
# Platforms API
# ---------------------------------------------------------------------------

@app.route("/api/platforms", methods=["GET"])
@require_auth
def list_platforms_route():
    include_archived = request.args.get("include_archived", "").lower() == "true"
    return jsonify(
        platforms_repo.list_platforms(_engine, include_archived=include_archived)
    )


@app.route("/api/platforms", methods=["POST"])
@require_auth
def create_platform():
    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return _bad("name is required.")
    platform = platforms_repo.create(
        _engine, name=data["name"], description=data.get("description")
    )
    return jsonify(platform), 201


@app.route("/api/platforms/<name>", methods=["PATCH"])
@require_auth
def update_platform(name: str):
    data = request.get_json(silent=True) or {}
    if "name" in data and data["name"] != name:
        result = platforms_repo.rename(_engine, name, data["name"])
    elif data.get("archived") is True:
        result = platforms_repo.archive(_engine, name)
    else:
        result = platforms_repo.get(_engine, name)
    if result is None:
        return _bad(f"Platform '{name}' not found.", 404)
    return jsonify(result)


# ---------------------------------------------------------------------------
# Auth — QR code magic link (unauthenticated)
# ---------------------------------------------------------------------------

@app.route("/auth/qr")
@limiter.limit(QR_RATE_LIMIT)
def auth_qr():
    """Return a PNG QR code encoding a magic-link URL with the bearer token.

    Intentionally unauthenticated: the mobile device has no token yet.
    Rate-limited to 20 req/min to prevent brute-force enumeration.
    """
    import io
    import qrcode  # type: ignore[import]

    magic_url = f"http://{request.host}/?token={_TOKEN}"
    img = qrcode.make(magic_url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    from flask import send_file
    return send_file(buf, mimetype="image/png")


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Method not allowed"}), 405


@app.errorhandler(413)
def payload_too_large(e):
    return jsonify({"error": f"File too large (max {MAX_UPLOAD_MB} MB)"}), 413


@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({"error": "Rate limit exceeded"}), 429


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    host = os.environ.get("BUGTRACKER_HOST", "0.0.0.0")
    port = int(os.environ.get("BUGTRACKER_PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true")
    app.run(host=host, port=port, debug=debug)
