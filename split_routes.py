#!/usr/bin/env python3
"""Script to split app.py into Flask blueprints."""

import re

# Read app.py
with open('app.py', 'r') as f:
    content = f.read()

# Define blueprint templates
BUGS_BP = '''"""Bug routes blueprint."""

from flask import Blueprint, g, jsonify, request
from pydantic import ValidationError

import db.annotations as annotations_repo
import db.artifacts as artifacts_repo
import db.bugs as bugs_repo
import db.relations as relations_repo
from schemas import BugCreate, CloseRequest

bugs_bp = Blueprint("bugs", __name__, url_prefix="/bugs")

def init_bugs(engine, search_backend, bug_service, require_auth_dec, bad_helper, bug_or_404_helper):
    """Initialize bugs blueprint with dependencies."""
    global _engine, _search, _bug_service, require_auth, _bad, _bug_or_404
    _engine = engine
    _search = search_backend
    _bug_service = bug_service
    require_auth = require_auth_dec
    _bad = bad_helper
    _bug_or_404 = bug_or_404_helper

'''

ARTIFACTS_BP = '''"""Artifact routes blueprint."""

from pathlib import Path
from flask import Blueprint, Response, g, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

import db.artifacts as artifacts_repo

artifacts_bp = Blueprint("artifacts", __name__)

def init_artifacts(engine, uploads_dir, allowed_file_func, require_auth_dec, bad_helper, bug_or_404_helper):
    """Initialize artifacts blueprint with dependencies."""
    global _engine, _UPLOADS_DIR, _allowed_file, require_auth, _bad, _bug_or_404
    _engine = engine
    _UPLOADS_DIR = uploads_dir
    _allowed_file = allowed_file_func
    require_auth = require_auth_dec
    _bad = bad_helper
    _bug_or_404 = bug_or_404_helper

'''

ADMIN_BP = '''"""Admin routes blueprint."""

from flask import Blueprint, g, jsonify, request

import db.agents as agents_repo
import db.areas as areas_repo
import db.platforms as platforms_repo
import db.products as products_repo
import db.severities as severities_repo

admin_bp = Blueprint("admin", __name__)

def init_admin(engine, require_auth_dec, bad_helper):
    """Initialize admin blueprint with dependencies."""
    global _engine, require_auth, _bad
    _engine = engine
    require_auth = require_auth_dec
    _bad = bad_helper

'''

# Extract routes
bugs_routes = re.findall(
    r'(@app\.route\("/bugs[^"]*"[^)]*\)[^@]*?def [^(]+\([^)]*\):.*?)(?=\n@app\.route|\n# -+\n|\nif __name__|\Z)',
    content,
    re.DOTALL
)

# Convert to blueprints
bugs_content = BUGS_BP
for route in bugs_routes:
    if '/artifacts' not in route and '/annotations' not in route and '/relations' not in route:
        # Convert @app.route to @bugs_bp.route and remove /bugs prefix
        converted = route.replace('@app.route("/bugs', '@bugs_bp.route("')
        bugs_content += '\n' + converted + '\n'

# Save bugs blueprint
with open('routes/bugs.py', 'w') as f:
    f.write(bugs_content)

print(f"Created routes/bugs.py with {len(bugs_routes)} routes")
print("Blueprint splitting complete!")
print("Note: Manual review needed for remaining routes (artifacts, annotations, admin)")
