"""Artifact routes blueprint."""
from pathlib import Path
import secrets as _secrets
from flask import Blueprint, Response, g, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename
import db.artifacts as artifacts_repo

artifacts_bp = Blueprint("artifacts", __name__)

_require_auth = None
_engine = None
_UPLOADS_DIR = None
_allowed_file = None
ALLOWED_EXTENSIONS = None
_bad = None
_bug_or_404 = None

def require_auth(f):
    def wrapper(*args, **kwargs):
        return _require_auth(f)(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

def init_artifacts(engine, uploads_dir, allowed_file_func, allowed_ext, require_auth_dec, bad, bug_or_404):
    global _engine, _UPLOADS_DIR, _allowed_file, ALLOWED_EXTENSIONS, _require_auth, _bad, _bug_or_404
    _engine, _UPLOADS_DIR, _allowed_file = engine, uploads_dir, allowed_file_func
    ALLOWED_EXTENSIONS, _require_auth, _bad, _bug_or_404 = allowed_ext, require_auth_dec, bad, bug_or_404

@artifacts_bp.route("/bugs/<bug_id>/artifacts", methods=["POST"])
@require_auth
def upload_artifact(bug_id: str):
    _, err = _bug_or_404(bug_id)
    if err:
        return err
    if "file" not in request.files:
        return _bad("file is required.")
    file = request.files["file"]
    filename = file.filename or "upload"
    if not _allowed_file(filename):
        return _bad(f"File type not allowed. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}", 400)
    safe_filename_base = secure_filename(filename)
    if not safe_filename_base:
        safe_filename_base = "upload"
    dest_dir = _UPLOADS_DIR / bug_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_name = _secrets.token_hex(4) + "_" + safe_filename_base
    dest_path = dest_dir / safe_name
    file.save(dest_path)
    relative_path = str(Path(bug_id) / safe_name)
    artifact = artifacts_repo.create(
        _engine, bug_id=bug_id, filename=filename, path=relative_path,
        mime_type=file.content_type, actor=g.actor, actor_type=g.actor_type)
    return jsonify(artifact), 201

@artifacts_bp.route("/bugs/<bug_id>/artifacts/<int:artifact_id>", methods=["GET"])
@require_auth
def download_artifact(bug_id: str, artifact_id: int):
    artifact = artifacts_repo.get(_engine, artifact_id)
    if artifact is None or artifact["bug_id"] != bug_id:
        return _bad("Artifact not found.", 404)
    abs_path = _UPLOADS_DIR / artifact["path"]
    resp = send_from_directory(
        str(abs_path.parent), abs_path.name,
        as_attachment=True, download_name=artifact["filename"])
    resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp
