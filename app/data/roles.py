"""
Roles storage (the `roles` table): list / create / update / delete, plus the
raw readers (menu / editable) used by the permission layer.

The *decisions* built on these readers (can this role view/edit a module, …)
live in ``app.permissions``.
"""

import re

from app import db
from app.config import BUILTIN_ROLE_MENUS, ROLE_LABELS


def _split(s):
    return [m for m in (s or "").split(",") if m]


def _slugify(label):
    s = re.sub(r"[^a-z0-9]+", "_", (label or "").strip().lower()).strip("_")
    return s or "role"


def _clean_menu(menu):
    """Normalise a menu to a clean list of module keys; 'home' is always first."""
    if isinstance(menu, str):
        menu = menu.split(",")
    out = ["home"]
    for m in (menu or []):
        m = (m or "").strip()
        if m and m not in out:
            out.append(m)
    return out


def _clean_editable(menu, editable):
    """Editable modules must be a subset of the visible (menu) modules."""
    if isinstance(editable, str):
        editable = editable.split(",")
    menu_set = set(menu)
    out = []
    for m in (editable or []):
        m = (m or "").strip()
        if m and m in menu_set and m not in out:
            out.append(m)
    return out


def _role_row_to_dict(r):
    keys = r.keys() if hasattr(r, "keys") else r
    editable = r["editable"] if "editable" in keys else ""
    return {"key": r["key"], "label": r["label"],
            "menu": _split(r["menu"]),
            "editable": _split(editable),
            "builtin": bool(r["builtin"])}


def list_roles():
    """All roles with their allowed modules. Built-in roles come first."""
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT * FROM roles ORDER BY builtin DESC, label").fetchall()
    return [_role_row_to_dict(r) for r in rows]


def role_label(key):
    with db.connect() as conn:
        row = conn.execute("SELECT label FROM roles WHERE key = ?", (key,)).fetchone()
    return row["label"] if row else ROLE_LABELS.get(key, key)


# --- raw readers (used by app.permissions) --------------------------------

def role_menu(key):
    """Module keys a role may SEE (always includes home)."""
    with db.connect() as conn:
        row = conn.execute("SELECT menu FROM roles WHERE key = ?", (key,)).fetchone()
    if not row:
        return ["home"]
    return _split(row["menu"]) or ["home"]


def role_editable(key):
    """Module keys a role may EDIT."""
    with db.connect() as conn:
        row = conn.execute("SELECT editable FROM roles WHERE key = ?", (key,)).fetchone()
    return _split(row["editable"]) if row else []


# --- CRUD -----------------------------------------------------------------

def create_role(label, menu, editable=None):
    label = (label or "").strip()
    if not label:
        return False, "Role name is required.", None
    menu = _clean_menu(menu)
    editable = _clean_editable(menu, editable or [])
    base = _slugify(label)
    with db.connect() as conn:
        key, n = base, 2
        while conn.execute("SELECT 1 FROM roles WHERE key = ?", (key,)).fetchone():
            key, n = f"{base}_{n}", n + 1
        conn.execute(
            "INSERT INTO roles (key, label, menu, editable, builtin) "
            "VALUES (?, ?, ?, ?, 0)",
            (key, label, ",".join(menu), ",".join(editable)))
        conn.commit()
    return True, "Role created.", key


def update_role(key, label, menu, editable=None):
    """Rename a role and/or change which modules it can see and edit."""
    label = (label or "").strip()
    if not label:
        return False, "Role name is required."
    menu = _clean_menu(menu)
    editable = _clean_editable(menu, editable or [])
    # The admin role must always keep full access so it can't lock itself out.
    if key == "admin":
        for m in BUILTIN_ROLE_MENUS["admin"].split(","):
            if m not in menu:
                menu.append(m)
        editable = list(menu)
    with db.connect() as conn:
        if not conn.execute("SELECT 1 FROM roles WHERE key = ?", (key,)).fetchone():
            return False, "Role not found."
        conn.execute(
            "UPDATE roles SET label = ?, menu = ?, editable = ? WHERE key = ?",
            (label, ",".join(menu), ",".join(editable), key))
        conn.commit()
    return True, "Role updated."


def delete_role(key):
    # The Administrator role must always exist; everything else is deletable.
    if key == "admin":
        return False, "The Administrator role can't be deleted."
    with db.connect() as conn:
        row = conn.execute("SELECT builtin FROM roles WHERE key = ?", (key,)).fetchone()
        if not row:
            return False, "Role not found."
        used = conn.execute("SELECT COUNT(*) AS c FROM users WHERE role = ?",
                            (key,)).fetchone()["c"]
        if used:
            return False, f"{used} account(s) still use this role. Reassign them first."
        conn.execute("DELETE FROM roles WHERE key = ?", (key,))
        if row["builtin"]:
            # Remember it was intentionally removed so init_db won't re-seed it.
            cur = conn.execute(
                "SELECT value FROM settings WHERE key = 'deleted_builtins'").fetchone()
            keys = set(filter(None, (cur["value"].split(",") if cur else [])))
            keys.add(key)
            conn.execute(
                "INSERT INTO settings (key, value) VALUES ('deleted_builtins', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (",".join(sorted(keys)),))
        conn.commit()
    return True, "Role deleted."
