"""
Audit trails: password changes, the edit log, and the unified Activity Log.

No sensitive data (passwords, raw arguments) is ever recorded here — only who
did what, when, and a short human label of what was touched.
"""

from app import db


# --------------------------------------------------------------------------
# Password-change trail
# --------------------------------------------------------------------------

def log_password_change(target, actor, kind="reset"):
    """Record a password change. `target`/`actor` are user-row dicts; we snapshot
    their name/username so the log stays readable even if an account is later
    renamed or deleted. `kind` is one of: self, reset, account_edit."""
    def _name(u):
        return (u or {}).get("full_name") or (u or {}).get("name") or "(unknown)"
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO password_changes (target_user_id, target_name, "
            "target_username, actor_user_id, actor_name, actor_username, kind, "
            "created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ((target or {}).get("id"), _name(target),
             (target or {}).get("username") or "(unknown)",
             (actor or {}).get("id"), _name(actor),
             (actor or {}).get("username") or "(unknown)", kind, db.now()))
        conn.commit()


def password_changes(limit=200):
    """Most-recent-first list of password changes for the admin audit view."""
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT * FROM password_changes ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


# --------------------------------------------------------------------------
# Edit log + unified Activity Log
# --------------------------------------------------------------------------

def log_edit(user, module, action, detail=""):
    """Record one data-changing action. `user` is the logged-in user dict;
    `action` is a human label and `detail` names what changed. No sensitive
    data here."""
    u = user or {}
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO edit_log (user_id, username, full_name, role, module, action, "
            "detail, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (u.get("id"), u.get("username") or "", u.get("full_name") or "",
             u.get("role") or "", module or "", action or "", (detail or "")[:300], db.now()))
        conn.commit()


def log_login(event, user=None, username="", ip=""):
    """Record a sign-in event. `event` is 'login' (success), 'failed' or
    'logout'. On failure `user` is None and `username` is the attempted name."""
    u = user or {}
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO login_log (user_id, username, full_name, role, event, ip, "
            "created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (u.get("id"), (u.get("username") or username or ""), u.get("full_name") or "",
             u.get("role") or "", event, (ip or "")[:64], db.now()))
        conn.commit()


# Timestamps are "YYYY-MM-DD HH:MM" → a lexicographic sort is chronological.
def _by_when_desc(events, limit):
    events.sort(key=lambda e: e["when"] or "", reverse=True)
    return events[:limit]


def _edit_events(conn, limit):
    """The 'edit' category: every data change (edit_log)."""
    events = []
    for r in conn.execute(
            "SELECT * FROM edit_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall():
        events.append({
            "src": "edit", "ref": r["id"], "when": r["created_at"], "category": "edit",
            "who": r["full_name"] or r["username"] or "Someone",
            "username": r["username"], "role": r["role"],
            "action": r["action"], "module": r["module"],
            "detail": r["detail"] if "detail" in r.keys() else "",
            "can_delete": True})
    return _by_when_desc(events, limit)


def _login_events(conn, limit):
    """The 'login' category: successful, failed and sign-out events (login_log)."""
    events = []
    for r in conn.execute(
            "SELECT * FROM login_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall():
        failed = r["event"] == "failed"
        action = ("Failed sign-in" if failed
                  else "Signed out" if r["event"] == "logout" else "Signed in")
        events.append({
            "src": "login", "ref": r["id"], "when": r["created_at"], "category": "login",
            "who": r["full_name"] or r["username"] or "Someone",
            "username": r["username"], "role": r["role"],
            "action": action, "module": "login",
            "detail": ("from " + r["ip"]) if r["ip"] else "",
            "can_delete": True, "failed": failed})
    return _by_when_desc(events, limit)


def activity_log(limit=400):
    """The admin Activity Log as SEPARATE per-category lists — never merged.

    Returns ``{"login": [...], "edit": [...]}``; each list is built from its own
    source, is most-recent-first, and is independently capped at `limit`. Keeping
    the categories apart means a burst in one (e.g. a bulk import) can never bury
    the other category's history."""
    limit = int(limit)
    with db.connect() as conn:
        return {
            "login": _login_events(conn, limit),
            "edit": _edit_events(conn, limit),
        }


def delete_edit(entry_id):
    """Remove one edit_log row (admin log cleanup)."""
    with db.connect() as conn:
        conn.execute("DELETE FROM edit_log WHERE id = ?", (int(entry_id),))
        conn.commit()
    return True


def delete_login_record(entry_id):
    """Remove one login_log row (admin log cleanup)."""
    with db.connect() as conn:
        conn.execute("DELETE FROM login_log WHERE id = ?", (int(entry_id),))
        conn.commit()
    return True
