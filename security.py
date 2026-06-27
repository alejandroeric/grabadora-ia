"""Seguridad: rate limiting en memoria + login simple por contraseña.

- Rate limiter casero (suficiente para una sola instancia en Render free),
  sin dependencias extra.
- Auth por contraseña única (APP_PASSWORD). Si no se configura, la app queda
  abierta (cómodo para desarrollo local).
"""
import time
from collections import defaultdict, deque
from functools import wraps

from flask import current_app, jsonify, redirect, request, session, url_for

# ---------- Rate limiter en memoria ----------
_hits = defaultdict(deque)


def _client_ip():
    fwd = request.headers.get("X-Forwarded-For", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.remote_addr or "?"


def rate_limit(max_calls, per_seconds):
    """Limita a max_calls por ventana de per_seconds, por IP y por endpoint."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            key = f"{fn.__name__}:{_client_ip()}"
            now = time.time()
            dq = _hits[key]
            while dq and dq[0] <= now - per_seconds:
                dq.popleft()
            if len(dq) >= max_calls:
                return jsonify({"error": "Demasiados pedidos. Esperá un momento."}), 429
            dq.append(now)
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ---------- Auth simple por contraseña ----------
def auth_enabled():
    return bool(current_app.config.get("APP_PASSWORD"))


def is_authed():
    return session.get("authed") is True


def require_auth(fn):
    """Protege una ruta: si hay APP_PASSWORD y no estás logueado, te frena."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if auth_enabled() and not is_authed():
            if request.path.startswith("/api/"):
                return jsonify({"error": "No autenticado."}), 401
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper
