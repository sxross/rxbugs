"""Authentication and authorization helpers.

Extracted from ``app.py`` so route modules stay focused on business logic.
"""

from __future__ import annotations

from functools import wraps

from flask import Response, g, jsonify, request


def make_authenticator(token: str, engine):
    """Return an ``_authenticate`` closure bound to the given *token* and *engine*.

    The closure checks the ``Authorization`` header for either the human token
    or a valid agent key, returning ``(actor_name, actor_type)`` on success.
    """
    import db.agents as agents_repo

    def _authenticate() -> tuple[str, str] | None:
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None
        bearer = auth[7:]
        if bearer == token:
            return ("human", "human")
        agent = agents_repo.authenticate(engine, bearer)
        if agent:
            return (agent["name"], "agent")
        return None

    return _authenticate


def require_auth(f):
    """Decorator that enforces authentication on a Flask route.

    ``_authenticate`` must already be registered via :func:`init_auth`.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        identity = _current_authenticator()
        if identity is None:
            return jsonify({"error": "Unauthorized"}), 401
        g.actor, g.actor_type = identity
        return f(*args, **kwargs)
    return decorated


def bad(msg: str, status: int = 400) -> Response:
    """Return a JSON error response."""
    return jsonify({"error": msg}), status


# ---------------------------------------------------------------------------
# Module-level state — set once at startup via init_auth()
# ---------------------------------------------------------------------------

_current_authenticator = None  # type: ignore[assignment]


def init_auth(token: str, engine) -> None:
    """Wire up the authenticator for the running app.

    Must be called once during startup (before any request is served).
    """
    global _current_authenticator
    _current_authenticator = make_authenticator(token, engine)
