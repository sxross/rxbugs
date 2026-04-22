"""RxBugs — Flask application entry point.

Starts the server, runs Alembic migrations on first launch,
and defines all API routes.
"""

from __future__ import annotations

import os
import sys
from functools import wraps
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
from pydantic import ValidationError
from schemas import BugCreate, CloseRequest
from services import BugService

_engine = init_engine()
_search = make_search_backend(_engine)
_bug_service = BugService(_engine)

# Run Alembic migrations on startup (idempotent — safe to run every time)
# Guarded by RUN_MIGRATIONS env var to prevent accidental production runs
from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig

def _run_migrations() -> None:
    cfg = AlembicConfig(str(Path(__file__).parent / "alembic.ini"))
    cfg.set_main_option(
        "script_location", str(Path(__file__).parent / "alembic")
    )
    alembic_command.upgrade(cfg, "head")

if os.environ.get("RUN_MIGRATIONS", "false").lower() in ("true", "1", "yes"):
    _run_migrations()

# ---------------------------------------------------------------------------
# Flask app + rate limiter
# ---------------------------------------------------------------------------

from flask import Flask, Response, g, jsonify, request, send_from_directory
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB upload limit

_UPLOADS_DIR = Path(__file__).parent / "uploads"
_UPLOADS_DIR.mkdir(exist_ok=True)

# File upload security: allowed extensions and size limits
ALLOWED_EXTENSIONS = {
    # Images
    "png", "jpg", "jpeg", "gif", "bmp", "webp", "svg",
    # Documents
    "pdf", "txt", "md", "rst",
    # Logs
    "log", "csv", "json", "xml", "yaml", "yml",
    # Archives
    "zip", "tar", "gz", "bz2",
    # Code/config
    "py", "js", "ts", "html", "css",
}

MAX_FILE_SIZE_MB = {
    "image": 10,  # 10 MB for images
    "default": 50,  # 50 MB for everything else
}

def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Rate limiter: Use Redis if available, fall back to in-memory (dev only)
_REDIS_URL = os.environ.get("REDIS_URL")
if _REDIS_URL:
    _storage_uri = _REDIS_URL
else:
    _storage_uri = "memory://"
    print("WARNING: Using in-memory rate limiter (dev only). Set REDIS_URL for production.", file=sys.stderr)

limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per minute"],
    storage_uri=_storage_uri,
)

# ---------------------------------------------------------------------------
# Session token storage for QR code auth (5-minute expiry)
# ---------------------------------------------------------------------------

import secrets
import time
from threading import Lock

_session_tokens: dict[str, float] = {}  # token -> expiry_timestamp
_session_lock = Lock()
_SESSION_TTL = 300  # 5 minutes

def _create_session_token() -> str:
    """Generate a short-lived session token for QR code auth."""
    token = secrets.token_urlsafe(16)
    expiry = time.time() + _SESSION_TTL
    with _session_lock:
        # Clean up expired tokens
        now = time.time()
        expired = [t for t, exp in _session_tokens.items() if exp < now]
        for t in expired:
            del _session_tokens[t]
        # Store new token
        _session_tokens[token] = expiry
    return token

def _validate_session_token(token: str) -> bool:
    """Validate and consume a session token (one-time use)."""
    with _session_lock:
        expiry = _session_tokens.get(token)
        if expiry is None:
            return False
        if time.time() > expiry:
            del _session_tokens[token]
            return False
        # Consume token (one-time use)
        del _session_tokens[token]
        return True

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

import db.agents as agents_repo


def _authenticate() -> tuple[str, str] | None:
    """Validate the Authorization header.

    Returns ``(actor_name, actor_type)`` or None if invalid.
    'actor_type' is 'human' for the BUGTRACKER_TOKEN, 'agent' for agent keys.
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:]
    if token == _TOKEN:
        return ("human", "human")
    agent = agents_repo.authenticate(_engine, token)
    if agent:
        return (agent["name"], "agent")
    return None


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        identity = _authenticate()
        if identity is None:
            return jsonify({"error": "Unauthorized"}), 401
        g.actor, g.actor_type = identity
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bad(msg: str, status: int = 400) -> Response:
    return jsonify({"error": msg}), status


def _bug_or_404(bug_id: str):
    from db import bugs as bugs_repo
    bug = bugs_repo.get(_engine, bug_id)
    if bug is None:
        return None, _bad(f"Bug '{bug_id}' not found.", 404)
    return bug, None


# ---------------------------------------------------------------------------
# Auth endpoints (QR code + session tokens)
# ---------------------------------------------------------------------------

@app.route("/auth/session", methods=["POST"])
@require_auth
def create_session():
    """Create a short-lived session token for QR code auth."""
    token = _create_session_token()
    return jsonify({"session_token": token, "expires_in": _SESSION_TTL})


@app.route("/auth/qr", methods=["GET"])
@require_auth
def get_qr_code():
    """Generate QR code containing a session login URL."""
    import io
    import qrcode
    
    # Create session token
    session_token = _create_session_token()
    
    # Build login URL (use request host for flexibility)
    base_url = request.url_root.rstrip("/")
    login_url = f"{base_url}/auth/login?session={session_token}"
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(login_url)
    qr.make(fit=True)
    
    # Render as SVG
    img_io = io.BytesIO()
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(img_io, format="PNG")
    img_io.seek(0)
    
    return Response(img_io.getvalue(), mimetype="image/png")


@app.route("/auth/login", methods=["GET"])
def session_login():
    """Validate session token and redirect to app with auth token."""
    session_token = request.args.get("session")
    if not session_token or not _validate_session_token(session_token):
        return "<h1>Invalid or expired session token</h1><p>Please scan the QR code again.</p>", 403
    
    # Return HTML that sets token in localStorage and redirects
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>RxBugs - Login</title>
</head>
<body>
    <h1>Logging you in...</h1>
    <script>
        localStorage.setItem('bugtracker_token', '{_TOKEN}');
        window.location.href = '/';
    </script>
</body>
</html>"""
    return html


# ---------------------------------------------------------------------------
# SPA shell
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


# ---------------------------------------------------------------------------
# Bugs — list / create
# ---------------------------------------------------------------------------

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
    
    # Pagination
    if request.args.get("page"):
        try:
            filters["page"] = int(request.args["page"])
        except ValueError:
            return _bad("page must be an integer.")
    if request.args.get("per_page"):
        try:
            filters["per_page"] = int(request.args["per_page"])
        except ValueError:
            return _bad("per_page must be an integer.")

    return jsonify(_search.query(filters))


@app.route("/bugs", methods=["POST"])
@require_auth
def create_bug():
    data = request.get_json(silent=True) or {}
    try:
        schema = BugCreate.model_validate(data)
    except ValidationError as exc:
        error = exc.errors()[0]
        field = error["loc"][0] if error["loc"] else "field"
        msg = error["msg"]
        return _bad(f"{field} {msg.lower()}" if msg == "Field required" else f"{field}: {msg}", 400)

    bug = bugs_repo.create(
        _engine,
        product=schema.product,
        title=schema.title,
        description=schema.description,
        area=schema.area,
        platform=schema.platform,
        priority=schema.priority,
        severity=schema.severity,
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
    try:
        schema = CloseRequest.model_validate(data)
    except ValidationError as exc:
        error = exc.errors()[0]
        field = error["loc"][0] if error["loc"] else "field"
        msg = error["msg"]
        return _bad(f"{field} {msg.lower()}" if msg == "Field required" else f"{field}: {msg}", 400)

    try:
        result = _bug_service.close_bug_with_annotation(
            bug_id=bug_id,
            resolution=schema.resolution,
            annotation_body=schema.annotation,
            actor=g.actor,
            actor_type=g.actor_type,
        )
    except ValueError as exc:
        return _bad(str(exc), 409)
    
    return jsonify(result)


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
    
    # Validate file extension
    if not _allowed_file(filename):
        return _bad(f"File type not allowed. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}", 400)
    
    # Sanitize filename
    safe_filename_base = secure_filename(filename)
    if not safe_filename_base:
        safe_filename_base = "upload"

    dest_dir = _UPLOADS_DIR / bug_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    # Avoid collisions by prepending a short random prefix
    import secrets as _secrets
    safe_name = _secrets.token_hex(4) + "_" + safe_filename_base
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
    resp = send_from_directory(
        str(abs_path.parent),
        abs_path.name,
        as_attachment=True,
        download_name=artifact["filename"],
    )
    # Prevent MIME sniffing attacks
    resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp


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
        rate_limit=int(data.get("rate_limit", 60)),
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
        result = products_repo._get(_engine, name)  # type: ignore[attr-defined]
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
        result = areas_repo._get(_engine, name)  # type: ignore[attr-defined]
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
        result = severities_repo._get(_engine, name)  # type: ignore[attr-defined]
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
        result = platforms_repo._get(_engine, name)  # type: ignore[attr-defined]
    if result is None:
        return _bad(f"Platform '{name}' not found.", 404)
    return jsonify(result)


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
    return jsonify({"error": "File too large (max 50 MB)"}), 413


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
