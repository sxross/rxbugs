"""RxBugs — Flask application entry point.

Registers blueprints and initializes the application.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Pre-flight checks
_TOKEN = os.environ.get("BUGTRACKER_TOKEN")
if not _TOKEN:
    print("ERROR: BUGTRACKER_TOKEN environment variable is not set.", file=sys.stderr)
    print("Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\"", file=sys.stderr)
    sys.exit(1)

# Database + migrations
from db.connection import init_engine, make_search_backend
from services import BugService

_engine = init_engine()
_search = make_search_backend(_engine)
_bug_service = BugService(_engine)

from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig

def _run_migrations() -> None:
    cfg = AlembicConfig(str(Path(__file__).parent / "alembic.ini"))
    cfg.set_main_option("script_location", str(Path(__file__).parent / "alembic"))
    alembic_command.upgrade(cfg, "head")

if os.environ.get("RUN_MIGRATIONS", "false").lower() in ("true", "1", "yes"):
    _run_migrations()

# Flask app + rate limiter
from flask import Flask, Response, g, jsonify, request, send_from_directory
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

ALLOWED_EXTENSIONS = {
    "png", "jpg", "jpeg", "gif", "bmp", "webp", "svg",
    "pdf", "txt", "md", "rst", "log", "csv", "json", "xml", "yaml", "yml",
    "zip", "tar", "gz", "bz2", "py", "js", "ts", "html", "css",
}

def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

_REDIS_URL = os.environ.get("REDIS_URL")
_storage_uri = _REDIS_URL if _REDIS_URL else "memory://"
if not _REDIS_URL:
    print("WARNING: Using in-memory rate limiter (dev only). Set REDIS_URL for production.", file=sys.stderr)

limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[DEFAULT_RATE_LIMIT],
    storage_uri=_storage_uri,
)

init_auth(_TOKEN, _engine)

def _bug_or_404(bug_id: str):
    from db import bugs as bugs_repo
    bug = bugs_repo.get(_engine, bug_id)
    if bug is None:
        return None, _bad(f"Bug '{bug_id}' not found.", 404)
    return bug, None

# Register blueprints
from routes import auth_bp, bugs_bp, artifacts_bp, admin_bp, openapi_bp
from routes.auth import init_auth
from routes.bugs import init_bugs
from routes.artifacts import init_artifacts
from routes.admin import init_admin

init_auth(require_auth, _TOKEN)
init_bugs(_engine, _search, _bug_service, require_auth, _bad, _bug_or_404)
init_artifacts(_engine, _UPLOADS_DIR, _allowed_file, ALLOWED_EXTENSIONS, require_auth, _bad, _bug_or_404)
init_admin(_engine, require_auth, _bad)

app.register_blueprint(auth_bp)
app.register_blueprint(bugs_bp)
app.register_blueprint(artifacts_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(openapi_bp)

# SPA shell
@app.route("/")
def index():
    return send_from_directory("static", "index.html")
# Error handlers
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

if __name__ == "__main__":
    host = os.environ.get("BUGTRACKER_HOST", "0.0.0.0")
    port = int(os.environ.get("BUGTRACKER_PORT", "5000"))
    app.run(host=host, port=port)
