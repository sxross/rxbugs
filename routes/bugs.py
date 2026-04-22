"""Bug routes blueprint."""
from flask import Blueprint, g, jsonify, request
from pydantic import ValidationError
import db.annotations as annotations_repo
import db.artifacts as artifacts_repo
import db.bugs as bugs_repo
import db.relations as relations_repo
from schemas import BugCreate, CloseRequest

bugs_bp = Blueprint("bugs", __name__, url_prefix="/bugs")

# Deferred decorator that will be set by init_bugs
_require_auth = None
_engine = None
_search = None
_bug_service = None
_bad = None
_bug_or_404 = None

def require_auth(f):
    """Wrapper that defers to actual auth decorator."""
    def wrapper(*args, **kwargs):
        return _require_auth(f)(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

def init_bugs(engine, search, bug_service, require_auth_dec, bad, bug_or_404):
    global _engine, _search, _bug_service, _require_auth, _bad, _bug_or_404
    _engine, _search, _bug_service = engine, search, bug_service
    _require_auth, _bad, _bug_or_404 = require_auth_dec, bad, bug_or_404

@bugs_bp.route("", methods=["GET"])
@require_auth
def list_bugs():
    from typing import Optional, List
    from db.types import BugFilters
    def _multi(key: str) -> Optional[List]:
        vals = request.args.getlist(key)
        return vals if vals else None
    filters: BugFilters = {}
    if request.args.get("q"):
        filters["q"] = request.args["q"]
    if _multi("product"):
        filters["product"] = _multi("product")  # type: ignore
    if _multi("area"):
        filters["area"] = _multi("area")  # type: ignore
    if _multi("platform"):
        filters["platform"] = _multi("platform")  # type: ignore
    if _multi("priority"):
        try:
            filters["priority"] = [int(p) for p in _multi("priority")]  # type: ignore
        except ValueError:
            return _bad("priority must be an integer.")
    if _multi("severity"):
        filters["severity"] = _multi("severity")  # type: ignore
    if request.args.get("status"):
        filters["status"] = request.args["status"]  # type: ignore
    if _multi("resolution"):
        filters["resolution"] = _multi("resolution")  # type: ignore
    if request.args.get("related_to"):
        filters["related_to"] = request.args["related_to"]
    if request.args.get("has_artifacts") is not None:
        filters["has_artifacts"] = request.args.get("has_artifacts", "").lower() == "true"
    if request.args.get("created_after"):
        filters["created_after"] = request.args["created_after"]
    if request.args.get("created_before"):
        filters["created_before"] = request.args["created_before"]
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

@bugs_bp.route("", methods=["POST"])
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
        _engine, product=schema.product, title=schema.title,
        description=schema.description, area=schema.area,
        platform=schema.platform, priority=schema.priority,
        severity=schema.severity, actor=g.actor, actor_type=g.actor_type)
    return jsonify(bug), 201

@bugs_bp.route("/<bug_id>", methods=["GET"])
@require_auth
def get_bug(bug_id: str):
    bug, err = _bug_or_404(bug_id)
    if err:
        return err
    annotations = annotations_repo.list_for_bug(_engine, bug_id)
    artifacts = artifacts_repo.list_for_bug(_engine, bug_id)
    related = relations_repo.list_for_bug(_engine, bug_id)
    return jsonify({**bug, "annotations": annotations,
        "artifacts": [{**a, "url": f"/bugs/{bug_id}/artifacts/{a['id']}"} for a in artifacts],
        "related_bugs": related})

@bugs_bp.route("/<bug_id>", methods=["PATCH"])
@require_auth
def update_bug(bug_id: str):
    bug, err = _bug_or_404(bug_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    updated = bugs_repo.update(_engine, bug_id, actor=g.actor, actor_type=g.actor_type, **data)
    return jsonify(updated)

@bugs_bp.route("/<bug_id>/close", methods=["POST"])
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
            bug_id=bug_id, resolution=schema.resolution,
            annotation_body=schema.annotation, actor=g.actor, actor_type=g.actor_type)
    except ValueError as exc:
        return _bad(str(exc), 409)
    return jsonify(result)

@bugs_bp.route("/<bug_id>/reopen", methods=["POST"])
@require_auth
def reopen_bug(bug_id: str):
    bug, err = _bug_or_404(bug_id)
    if err:
        return err
    try:
        updated = bugs_repo.reopen(_engine, bug_id, actor=g.actor, actor_type=g.actor_type)
    except ValueError as exc:
        return _bad(str(exc), 409)
    return jsonify(updated)

@bugs_bp.route("/<bug_id>/annotations", methods=["POST"])
@require_auth
def add_annotation(bug_id: str):
    _, err = _bug_or_404(bug_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    if not data.get("body"):
        return _bad("body is required.")
    annotation = annotations_repo.create(
        _engine, bug_id=bug_id, author=g.actor,
        author_type=g.actor_type, body=data["body"])
    return jsonify(annotation), 201

@bugs_bp.route("/<bug_id>/relations", methods=["POST"])
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
        relations_repo.link(_engine, bug_id, related_id, actor=g.actor, actor_type=g.actor_type)
    except ValueError as exc:
        return _bad(str(exc))
    return jsonify({"bug_id": bug_id, "related_id": related_id}), 201

@bugs_bp.route("/<bug_id>/relations/<related_id>", methods=["DELETE"])
@require_auth
def remove_relation(bug_id: str, related_id: str):
    existed = relations_repo.unlink(_engine, bug_id, related_id, actor=g.actor, actor_type=g.actor_type)
    if not existed:
        return _bad("Relation not found.", 404)
    return "", 204
