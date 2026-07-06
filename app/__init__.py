"""
Application factory.

``create_app()`` builds the Flask app: hardened session cookies, a strict set of
security response headers, the schema bootstrap, the API dispatcher and the
static front-end in ``web/``.

The same app serves the browser SPA over one Supabase Postgres database, so the
hosted site and any local run share identical code.
"""

import os
from datetime import timedelta

from flask import Flask, jsonify, send_from_directory

from app import schema
from app.routes import bp as api_bp

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(BASE_DIR, "web")

# A strict Content-Security-Policy. script-src is 'self' only (no inline scripts
# or event handlers exist). Inline styles are the only relaxation the UI needs;
# fonts are loaded from Google Fonts, so those origins are allowed.
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "object-src 'none'"
)


def _hosted():
    return bool(os.environ.get("VERCEL") or os.environ.get("SECURE_COOKIES"))


def create_app():
    app = Flask(__name__, static_folder=None)

    # Cookies are signed with this secret. It MUST be a stable, strong value in
    # production — a per-process random fallback would silently break sessions
    # across serverless instances, so we refuse to start hosted without it.
    secret = os.environ.get("SECRET_KEY")
    if not secret:
        if _hosted():
            raise RuntimeError(
                "SECRET_KEY is not set. Set a long random SECRET_KEY in the "
                "host environment before deploying.")
        secret = os.urandom(32)   # local dev only: fine to reset on restart
    app.secret_key = secret

    app.permanent_session_lifetime = timedelta(days=30)
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,                 # no JS access (XSS defence)
        SESSION_COOKIE_SAMESITE="Lax",                # blocks cross-site POST (CSRF)
        SESSION_COOKIE_SECURE=_hosted(),              # HTTPS-only when hosted
    )
    # __Host- cookie prefix when hosted: the browser then REFUSES the cookie unless
    # it is Secure, host-only (no Domain) and Path=/ — all of which Flask already
    # sets here. This hard-binds the session to this exact host, extra defence on
    # the shared `vercel.app` parent domain. Local dev keeps the plain name (the
    # prefix requires Secure, which we don't set over plain-HTTP dev). NOTE: the
    # rename signs every existing cookie out once on the deploy that ships it.
    if _hosted():
        app.config["SESSION_COOKIE_NAME"] = "__Host-session"

    # Create / migrate the schema and seed once at boot (cheap on a warm DB).
    schema.init_db()

    # API dispatcher.
    app.register_blueprint(api_bp)

    # ---- static front-end (web/) -------------------------------------------
    def _no_cache(resp):
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp

    @app.get("/")
    def index():
        return _no_cache(send_from_directory(WEB_DIR, "index.html"))

    _IMMUTABLE = (".js", ".css")
    _ASSETS = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp")

    @app.get("/<path:filename>")
    def static_files(filename):
        # send_from_directory safely rejects path traversal (../).
        resp = send_from_directory(WEB_DIR, filename)
        name = filename.lower()
        if name.endswith(_IMMUTABLE):
            # Code is always requested with a ?v=N cache-buster, so cache hard.
            resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            return resp
        if name.endswith(_ASSETS):
            resp.headers["Cache-Control"] = "public, max-age=604800"
            return resp
        return _no_cache(resp)

    # ---- security headers on every response --------------------------------
    @app.after_request
    def _security_headers(resp):
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
        resp.headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        resp.headers.setdefault("Permissions-Policy",
                                "camera=(), microphone=(), geolocation=()")
        # Cross-origin isolation: this is a standalone app, never framed or loaded
        # cross-site. COOP severs any cross-origin opener (popup/window) link; CORP
        # tells browsers our own resources may only be loaded same-origin. Neither
        # affects same-origin fetch/XHR or the Google Fonts <link> (that response's
        # CORP is set by Google, not us), so the SPA is unaffected.
        resp.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        resp.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        if _hosted():
            resp.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return resp

    # ---- custom error pages (suppress Flask HTML that leaks tech stack) -----
    @app.errorhandler(404)
    def _not_found(_e):
        return jsonify({"error": "Not found."}), 404

    @app.errorhandler(405)
    def _method_not_allowed(_e):
        return jsonify({"error": "Method not allowed."}), 405

    return app
