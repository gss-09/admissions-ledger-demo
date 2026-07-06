"""
The single request dispatcher: ``POST /api/<method>`` → ``Api.<method>(*args)``.

Order of checks (a request must pass each to proceed):
  1. method name is public-shaped (no leading underscore, not disallowed),
  2. authentication — a session is required for everything except PUBLIC. This is
     checked BEFORE existence so an anonymous caller can't tell a real protected
     method (401) from a bogus one (would-be 404) — no endpoint-enumeration oracle,
  3. the method actually exists on Api,
  4. revocation — the cookie is re-checked against the users table (every write,
     and at most every REVALIDATE_SECONDS for reads),
  5. arguments are a JSON list,
  6. authorization — the central gate in ``permissions.deny_reason`` (EDIT gate
     for writes, VIEW gate for metadata reads),
  7. the call runs; successful writes are appended to the audit log.
"""

import inspect
import time
from urllib.parse import urlsplit

from flask import Blueprint, request, session, jsonify

from app import permissions
from app.config import EDIT_ACTIONS, action_label
from app.data import audit, users as users_db
from app.endpoints import Api

bp = Blueprint("api", __name__)

# How long a session's cached identity may serve READS before it is re-checked
# against the users table. Writes are ALWAYS re-checked (see _session_invalid).
# Set to 0 = re-check EVERY request: a deleted, demoted or password-reset account
# loses both read AND write access immediately (no stale window where a revoked
# user keeps reading student PII or a demoted admin keeps elevated access). The
# cost is one indexed PK lookup per request, negligible at this app's scale — the
# main data reads already query the DB anyway. Raise it (e.g. 60/300) only if read
# latency from the per-request lookup ever becomes a concern.
REVALIDATE_SECONDS = 0


def _client_ip():
    """Best-effort client IP for the login throttle, the FIRST entry of
    X-Forwarded-For (the originating client), else the socket address.

    SECURITY — trusted-proxy assumption: this is only sound behind a proxy that
    *sanitises* X-Forwarded-For (overwrites any value the client sent). Vercel does
    exactly that — verified empirically: a spoofed X-Forwarded-For is ignored and
    the real client IP is what the function receives — so the per-IP throttle can't
    be evaded by rotating the header. If this app is ever moved off Vercel to a
    proxy that *appends* the client value instead of replacing it, this MUST change
    (pin the number of trusted hops / read the proxy's trusted header) or the per-IP
    throttle becomes bypassable."""
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.remote_addr or ""


@bp.before_request
def _reject_cross_origin():
    """CSRF belt-and-braces on top of SameSite=Lax cookies: browsers attach an
    Origin header to cross-site POSTs, so one that doesn't match the Host we are
    served as is refused. Host-only compare — behind Vercel's proxy Flask sees
    http while the public origin is https, so the scheme can't be trusted."""
    origin = request.headers.get("Origin")
    if origin and urlsplit(origin).netloc != request.host:
        return jsonify({"error": "Cross-origin requests are not allowed."}), 403


@bp.after_request
def _no_store(resp):
    # API responses are per-user; never let a browser or proxy cache them.
    resp.headers.setdefault("Cache-Control", "no-store")
    return resp


def _stamp_session(user_id):
    """Record a fingerprint of the user's current password hash (and a fresh
    re-check time) in the session, so a password reset elsewhere invalidates
    every other cookie for that account at its next re-check."""
    row = users_db.get_user(user_id)
    session["pwv"] = (row.get("password_hash") or "")[:16] if row else ""
    session["checked"] = time.time()


def _session_invalid(bridge, method):
    """Sessions are stateless signed cookies, so deleting a user, changing their
    role or resetting their password can't revoke a cookie by itself. This
    re-checks the cookie against the users table — on every write, and at most
    every REVALIDATE_SECONDS for reads — and signs the user out when the account
    no longer matches. Returns a (response, status) on invalidation, else None."""
    fresh = time.time() - float(session.get("checked") or 0) < REVALIDATE_SECONDS
    if fresh and method not in EDIT_ACTIONS:
        return None
    row = users_db.get_user(bridge.user["id"])
    pwv = session.get("pwv")
    ok = (row is not None
          and row.get("role") == bridge.user.get("role")
          and (not pwv or (row.get("password_hash") or "").startswith(pwv)))
    if not ok:
        session.clear()
        bridge.user = None
        return (jsonify({"ok": False, "error":
                         "Your session is no longer valid. Please sign in again."}), 401)
    bridge.user["full_name"] = row["full_name"]
    bridge.user["username"] = row["username"]
    bridge.user["role"] = row["role"]
    bridge.user["role_label"] = bridge.user.get("role_label")
    if pwv is None:   # cookie predates fingerprinting — stamp it now
        session["pwv"] = (row.get("password_hash") or "")[:16]
    session["checked"] = time.time()
    return None


@bp.post("/api/<method>")
def call_api(method):
    # 1. Shape check: underscore-prefixed / disallowed names are never endpoints.
    if method.startswith("_") or method in permissions.DISALLOWED:
        return jsonify({"error": "Unknown method."}), 404

    bridge = Api()
    bridge.user = session.get("user")   # who is logged in (if anyone)
    bridge._ip = _client_ip()           # for the per-IP login throttle

    # 2. Authentication gate — BEFORE the existence check, so an anonymous caller
    #    gets the same 401 for every non-public name whether the method exists or
    #    not. (If existence were checked first, a real-but-protected method would
    #    401 while a bogus one 404'd, letting an anonymous client enumerate the real
    #    endpoint names. The method names appear in the public JS anyway, but we
    #    don't volunteer a server-side oracle.)
    if method not in permissions.PUBLIC and not bridge.user:
        return jsonify({"ok": False, "error": "Not signed in."}), 401

    # 3. Existence check (an authenticated caller may still hit a typo → 404).
    fn = getattr(bridge, method, None)
    if not callable(fn) or inspect.ismethod(fn) is False:
        return jsonify({"error": "Unknown method."}), 404

    # 4. Revocation gate — bounce cookies whose account was deleted, re-roled or
    # password-reset since they were issued.
    if bridge.user and method not in ("login", "logout"):
        invalid = _session_invalid(bridge, method)
        if invalid is not None:
            return invalid

    # 5. Parse arguments.
    payload = request.get_json(silent=True) or {}
    args = payload.get("args", [])
    if not isinstance(args, list):
        return jsonify({"error": "Bad arguments."}), 400

    # 6. Authorization gate (EDIT for writes, VIEW for metadata reads).
    if method not in permissions.PUBLIC:
        denial = permissions.deny_reason(bridge.user, method)
        if denial is not None:
            body, status = denial
            return jsonify(body), status

    # 7. Run. Bad argument counts/values surface as a 400, not a 500 traceback.
    try:
        result = fn(*args)
    except (TypeError, ValueError):
        return jsonify({"error": "Bad arguments."}), 400

    # Audit successful data-changing actions (skip {"ok": False}).
    module = EDIT_ACTIONS.get(method)
    if module and not (isinstance(result, dict) and result.get("ok") is False):
        try:
            audit.log_edit(bridge.user, module, action_label(method),
                           getattr(bridge, "_detail", ""))
        except Exception:
            pass

    # Login audit: record every sign-in attempt (success + failure) with its IP.
    if method == "login":
        try:
            ip = _client_ip()
            if isinstance(result, dict) and result.get("ok"):
                audit.log_login("login", user=bridge.user, ip=ip)
            else:
                audit.log_login("failed", username=(args[0] if args else ""), ip=ip)
        except Exception:
            pass

    # A fresh login — or an action that may have changed the caller's OWN
    # password (so their fingerprint must follow it) — re-stamps the session.
    if (bridge.user and isinstance(result, dict) and result.get("ok")
            and method in ("login", "change_my_password", "users_update")):
        try:
            _stamp_session(bridge.user["id"])
        except Exception:
            pass

    # login()/logout()/users_update() may change who is logged in — persist it.
    if bridge.user is None:
        session.clear()
    else:
        session["user"] = bridge.user
        session.permanent = True
    return jsonify(result)
