"""Flask blueprints for RxBugs routes."""

from .auth import auth_bp
from .bugs import bugs_bp
from .artifacts import artifacts_bp
from .admin import admin_bp
from .openapi import openapi_bp

__all__ = ["auth_bp", "bugs_bp", "artifacts_bp", "admin_bp", "openapi_bp"]
