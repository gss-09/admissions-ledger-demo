"""User accounts: authentication, lookup and CRUD (the `users` table)."""

from app import db, security


def authenticate(username, password):
    """Return the user row (as dict) if credentials are valid, else None."""
    with db.connect() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if row and security.verify_password(password, row["password_hash"]):
        # Upgrade hashes stored at an older work factor while the plaintext is
        # available — the only moment a rehash is possible.
        if security.password_needs_rehash(row["password_hash"]):
            set_password(row["id"], password)
        return dict(row)
    return None


def list_users():
    """Every user, each with their CITY bindings (`city_ids` + `city_names`).
    No rows ⇒ org-wide (empty lists), per the scoping rule."""
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT * FROM users ORDER BY role, LOWER(username)").fetchall()
        binds = {}
        for r in conn.execute(
                "SELECT uc.user_id AS uid, ci.id AS cid, ci.name AS cname "
                "FROM user_cities uc JOIN cities ci ON ci.id = uc.city_id "
                "ORDER BY ci.name").fetchall():
            b = binds.setdefault(r["uid"], {"ids": [], "names": []})
            b["ids"].append(r["cid"])
            b["names"].append(r["cname"])
    out = []
    for r in rows:
        d = dict(r)
        b = binds.get(d["id"], {"ids": [], "names": []})
        d["city_ids"], d["city_names"] = b["ids"], b["names"]
        out.append(d)
    return out


def get_user(user_id):
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def admin_count():
    with db.connect() as conn:
        return int(conn.execute(
            "SELECT COUNT(*) AS c FROM users WHERE role = 'admin'").fetchone()["c"])


def create_user(username, full_name, role, password):
    """Insert one account. Returns (ok, message, user_id) — the id lets the caller
    set campus bindings on the fresh row."""
    with db.connect() as conn:
        try:
            uid = db.insert(conn,
                "INSERT INTO users (username, full_name, role, password_hash, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (username.strip(), full_name.strip(), role,
                 security.hash_password(password), db.now()))
            conn.commit()
            return True, "Account created.", uid
        except db.INTEGRITY_ERRORS:
            conn.rollback()
            return False, "That username already exists.", None


def update_user(user_id, full_name, username, role):
    with db.connect() as conn:
        try:
            conn.execute(
                "UPDATE users SET full_name = ?, username = ?, role = ? WHERE id = ?",
                (full_name.strip(), username.strip(), role, user_id))
            conn.commit()
            return True, "Account updated."
        except db.INTEGRITY_ERRORS:
            conn.rollback()
            return False, "That username already exists."


def delete_user(user_id):
    with db.connect() as conn:
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()


def set_password(user_id, password):
    with db.connect() as conn:
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                     (security.hash_password(password), user_id))
        conn.commit()


# --------------------------------------------------------------------------
# City bindings (SCHEMA_VERSION 11; superseded the campus bindings of v9). Empty
# set ⇒ org-wide (see schema/tables). A user is bound to 1..n CITIES.
# --------------------------------------------------------------------------

def user_city_ids(user_id):
    """The city ids a user is bound to (empty ⇒ org-wide). Drives the org-wide
    decision in `_campus_scope` (empty city set, not empty campus set, means
    org-wide — a city with no campuses yet must still scope, not open everything)."""
    with db.connect() as conn:
        return [r["city_id"] for r in conn.execute(
            "SELECT city_id FROM user_cities WHERE user_id = ?",
            (int(user_id),)).fetchall()]


def user_campus_names(user_id):
    """The campus NAMES in a user's CITY scope — every campus of every city they're
    bound to (cities expanded live). This is the row filter the data layer uses
    (`students.campus` is a name), so adding a campus to a bound city auto-includes
    it. Empty list ⇒ either no bindings (org-wide) or bound to empty cities; the
    org-wide vs empty-scope distinction is made by `user_city_ids` upstream."""
    with db.connect() as conn:
        return [r["name"] for r in conn.execute(
            "SELECT c.name AS name FROM user_cities uc "
            "JOIN campuses c ON c.city_id = uc.city_id WHERE uc.user_id = ? "
            "ORDER BY c.name", (int(user_id),)).fetchall()]


def set_user_cities(user_id, city_ids):
    """Replace a user's city bindings with exactly `city_ids` (validated, deduped).
    An empty list deletes every row ⇒ the user becomes org-wide."""
    uid = int(user_id)
    with db.connect() as conn:
        conn.execute("DELETE FROM user_cities WHERE user_id = ?", (uid,))
        seen = set()
        for cid in city_ids or []:
            try:
                cid = int(cid)
            except (TypeError, ValueError):
                continue
            if cid in seen:
                continue
            if conn.execute("SELECT 1 FROM cities WHERE id = ?", (cid,)).fetchone():
                conn.execute(
                    "INSERT INTO user_cities (user_id, city_id) VALUES (?, ?)",
                    (uid, cid))
                seen.add(cid)
        conn.commit()
