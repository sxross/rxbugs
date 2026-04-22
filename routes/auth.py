"""Authentication routes blueprint."""

import io
import secrets
import time
from threading import Lock

import qrcode
from flask import Blueprint, Response, jsonify, request, g

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

# Session token storage for QR code auth (5-minute expiry)
_session_tokens: dict[str, float] = {}
_session_lock = Lock()
_SESSION_TTL = 300

def _create_session_token() -> str:
    """Generate a short-lived session token for QR code auth."""
    token = secrets.token_urlsafe(16)
    expiry = time.time() + _SESSION_TTL
    with _session_lock:
        now = time.time()
        expired = [t for t, exp in _session_tokens.items() if exp < now]
        for t in expired:
            del _session_tokens[t]
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
        del _session_tokens[token]
        return True

_require_auth = None
_TOKEN = None

def require_auth(f):
    def wrapper(*args, **kwargs):
        return _require_auth(f)(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

def init_auth(require_auth_decorator, bugtracker_token):
    """Initialize auth blueprint with dependencies."""
    global _require_auth, _TOKEN
    _require_auth = require_auth_decorator
    _TOKEN = bugtracker_token

@auth_bp.route("/session", methods=["POST"])
@require_auth
def create_session():
    """Create a short-lived session token for QR code auth."""
    token = _create_session_token()
    return jsonify({"session_token": token, "expires_in": _SESSION_TTL})

@auth_bp.route("/qr", methods=["GET"])
@require_auth
def get_qr_code():
    """Generate QR code containing a session login URL."""
    session_token = _create_session_token()
    base_url = request.url_root.rstrip("/")
    login_url = f"{base_url}/auth/login?session={session_token}"
    
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(login_url)
    qr.make(fit=True)
    
    img_io = io.BytesIO()
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(img_io, format="PNG")
    img_io.seek(0)
    
    return Response(img_io.getvalue(), mimetype="image/png")

@auth_bp.route("/login", methods=["GET"])
def session_login():
    """Validate session token and redirect to app with auth token."""
    session_token = request.args.get("session")
    if not session_token or not _validate_session_token(session_token):
        return "<h1>Invalid or expired session token</h1><p>Please scan the QR code again.</p>", 403
    
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
