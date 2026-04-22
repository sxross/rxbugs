"""Admin routes blueprint."""
from flask import Blueprint, g, jsonify, request
import db.agents as agents_repo
import db.areas as areas_repo
import db.platforms as platforms_repo
import db.products as products_repo
import db.severities as severities_repo

admin_bp = Blueprint("admin", __name__)

_require_auth = None
_engine = None
_bad = None

def require_auth(f):
    def wrapper(*args, **kwargs):
        return _require_auth(f)(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

def init_admin(engine, require_auth_dec, bad):
    global _engine, _require_auth, _bad
    _engine, _require_auth, _bad = engine, require_auth_dec, bad

# Agents
@admin_bp.route("/agents", methods=["GET"])
@require_auth
def list_agents():
    return jsonify(agents_repo.list_agents(_engine))

@admin_bp.route("/agents", methods=["POST"])
@require_auth
def register_agent():
    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return _bad("name is required.")
    agent, raw_key = agents_repo.register(
        _engine, name=data["name"], description=data.get("description"),
        rate_limit=int(data.get("rate_limit", 60)))
    return jsonify({**agent, "key": raw_key}), 201

@admin_bp.route("/agents/<key>", methods=["DELETE"])
@require_auth
def revoke_agent(key: str):
    revoked = agents_repo.revoke(_engine, key)
    if not revoked:
        return _bad("Agent not found.", 404)
    return "", 204

# Products
@admin_bp.route("/api/products", methods=["GET"])
@require_auth
def list_products():
    include_archived = request.args.get("include_archived", "").lower() == "true"
    return jsonify(products_repo.list_products(_engine, include_archived=include_archived))

@admin_bp.route("/api/products", methods=["POST"])
@require_auth
def create_product():
    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return _bad("name is required.")
    product = products_repo.create(_engine, name=data["name"], description=data.get("description"))
    return jsonify(product), 201

@admin_bp.route("/api/products/<name>", methods=["PATCH"])
@require_auth
def update_product(name: str):
    data = request.get_json(silent=True) or {}
    if "name" in data and data["name"] != name:
        result = products_repo.rename(_engine, name, data["name"])
    elif data.get("archived") is True:
        result = products_repo.archive(_engine, name)
    else:
        result = products_repo._get(_engine, name)  # type: ignore
    if result is None:
        return _bad(f"Product '{name}' not found.", 404)
    return jsonify(result)

# Areas
@admin_bp.route("/api/areas", methods=["GET"])
@require_auth
def list_areas():
    include_archived = request.args.get("include_archived", "").lower() == "true"
    return jsonify(areas_repo.list_areas(_engine, include_archived=include_archived))

@admin_bp.route("/api/areas", methods=["POST"])
@require_auth
def create_area():
    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return _bad("name is required.")
    area = areas_repo.create(_engine, name=data["name"], description=data.get("description"))
    return jsonify(area), 201

@admin_bp.route("/api/areas/<name>", methods=["PATCH"])
@require_auth
def update_area(name: str):
    data = request.get_json(silent=True) or {}
    if "name" in data and data["name"] != name:
        result = areas_repo.rename(_engine, name, data["name"])
    elif data.get("archived") is True:
        result = areas_repo.archive(_engine, name)
    else:
        result = areas_repo._get(_engine, name)  # type: ignore
    if result is None:
        return _bad(f"Area '{name}' not found.", 404)
    return jsonify(result)

# Severities
@admin_bp.route("/api/severities", methods=["GET"])
@require_auth
def list_severities():
    include_archived = request.args.get("include_archived", "").lower() == "true"
    return jsonify(severities_repo.list_severities(_engine, include_archived=include_archived))

@admin_bp.route("/api/severities", methods=["POST"])
@require_auth
def create_severitie():
    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return _bad("name is required.")
    severitie = severities_repo.create(_engine, name=data["name"], description=data.get("description"))
    return jsonify(severitie), 201

@admin_bp.route("/api/severities/<name>", methods=["PATCH"])
@require_auth
def update_severitie(name: str):
    data = request.get_json(silent=True) or {}
    if "name" in data and data["name"] != name:
        result = severities_repo.rename(_engine, name, data["name"])
    elif data.get("archived") is True:
        result = severities_repo.archive(_engine, name)
    else:
        result = severities_repo._get(_engine, name)  # type: ignore
    if result is None:
        return _bad(f"Severitie '{name}' not found.", 404)
    return jsonify(result)

# Platforms
@admin_bp.route("/api/platforms", methods=["GET"])
@require_auth
def list_platforms():
    include_archived = request.args.get("include_archived", "").lower() == "true"
    return jsonify(platforms_repo.list_platforms(_engine, include_archived=include_archived))

@admin_bp.route("/api/platforms", methods=["POST"])
@require_auth
def create_platform():
    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return _bad("name is required.")
    platform = platforms_repo.create(_engine, name=data["name"], description=data.get("description"))
    return jsonify(platform), 201

@admin_bp.route("/api/platforms/<name>", methods=["PATCH"])
@require_auth
def update_platform(name: str):
    data = request.get_json(silent=True) or {}
    if "name" in data and data["name"] != name:
        result = platforms_repo.rename(_engine, name, data["name"])
    elif data.get("archived") is True:
        result = platforms_repo.archive(_engine, name)
    else:
        result = platforms_repo._get(_engine, name)  # type: ignore
    if result is None:
        return _bad(f"Platform '{name}' not found.", 404)
    return jsonify(result)
