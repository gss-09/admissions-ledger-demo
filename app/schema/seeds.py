"""Seeding: built-in roles (respecting admin deletions recorded in the
``deleted_builtins`` setting) and the first-run admin account with a RANDOM
password — no weak default credentials are ever written."""

import secrets

from app import db, security
from app.config import ROLES, ROLE_LABELS, BUILTIN_ROLE_MENUS, BUILTIN_ROLE_EDITABLE


def seed_builtin_roles(conn):
    # Seed any built-in roles not present yet (skip ones an admin deleted).
    _del = conn.execute(
        "SELECT value FROM settings WHERE key = 'deleted_builtins'").fetchone()
    _deleted_builtins = set(filter(None, (_del["value"].split(",") if _del else [])))
    for key in ROLES:
        if key in _deleted_builtins:
            continue
        if not conn.execute("SELECT 1 FROM roles WHERE key = ?", (key,)).fetchone():
            menu = BUILTIN_ROLE_MENUS.get(key, "home")
            editable = BUILTIN_ROLE_EDITABLE.get(key, menu)
            conn.execute(
                "INSERT INTO roles (key, label, menu, editable, builtin) "
                "VALUES (?, ?, ?, ?, 1)",
                (key, ROLE_LABELS.get(key, key), menu, editable))

    # Keep the admin role's stored menu in sync with the built-in set: a schema
    # bump that adds a module (e.g. `org`) must surface in the admin's nav, which
    # is built from the stored menu. Admin always has full access anyway (the
    # permission gates bypass it, and update_role enforces the same invariant), so
    # this only ever *adds* — it never narrows access. Skip if admin was deleted.
    if "admin" not in _deleted_builtins and conn.execute(
            "SELECT 1 FROM roles WHERE key = 'admin'").fetchone():
        full = BUILTIN_ROLE_MENUS["admin"]
        conn.execute("UPDATE roles SET menu = ?, editable = ? WHERE key = 'admin'",
                     (full, full))


# City → campus mapping for the SCHEMA_VERSION 7 hierarchy (idempotent seed).
CITY_CAMPUSES = {
    "NORTHVALE": ("NORTHVALE DS", "NORTHVALE HOSTEL"),
    "EASTPORT":  ("EASTPORT DS",),
    "WESTBROOK": ("WESTBROOK DS",),
}
# Campuses that carry every existing student today — seed the full course list
# under both so existing admissions validate against their campus's courses.
_SEED_COURSE_CAMPUSES = ("NORTHVALE DS", "NORTHVALE HOSTEL")
# Analytics screens that became their own modules in SCHEMA_VERSION 7. Any role
# that could already see the student data (had `students`) gains View on them, so
# nobody loses access on upgrade; an admin can then toggle each off per role.
_V7_STUDENT_DATA_MODULES = ("agms", "execs", "averages", "income", "expenditure")


def seed_org(conn):
    """Seed the recruiting org (idempotent):

    * the two default campuses (NORTHVALE DS, NORTHVALE HOSTEL);
    * backfill every existing student with no campus to NORTHVALE DS;
    * register the AGM names already present in the data, so the managed list
      starts populated and existing admissions stay valid;
    * SCHEMA_VERSION 7: the City → Campus → Course hierarchy, campus-bound AGMs,
      and the per-role analytics-module migration.
    """
    for name in ("NORTHVALE DS", "NORTHVALE HOSTEL"):
        if not conn.execute("SELECT 1 FROM campuses WHERE name = ?", (name,)).fetchone():
            conn.execute("INSERT INTO campuses (name, created_at) VALUES (?, ?)",
                         (name, db.now()))

    conn.execute(
        "UPDATE students SET campus = 'NORTHVALE DS' "
        "WHERE campus IS NULL OR campus = ''")

    for r in conn.execute(
            "SELECT DISTINCT agm AS v FROM students "
            "WHERE agm IS NOT NULL AND agm <> ''").fetchall():
        name = (r["v"] or "").strip()
        if name and not conn.execute(
                "SELECT 1 FROM agms WHERE name = ?", (name,)).fetchone():
            conn.execute("INSERT INTO agms (name, created_at) VALUES (?, ?)",
                         (name, db.now()))

    # The "NOT DECIDED" funnel stage was merged into "NOT LIFTING"; fold any
    # existing rows over. status_raw keeps the original imported wording.
    conn.execute(
        "UPDATE students SET status_category = 'NOT LIFTING' "
        "WHERE status_category = 'NOT DECIDED'")

    _seed_cities(conn)
    _seed_courses(conn)
    _seed_agm_campuses(conn)
    _migrate_role_menus(conn)
    _seed_city_bindings(conn)


def _seed_cities(conn):
    """Create the three cities and point each (existing) campus at its city.
    Only sets `city_id` when still null, so an admin's later re-assignment sticks."""
    for city, campuses in CITY_CAMPUSES.items():
        row = conn.execute("SELECT id FROM cities WHERE name = ?", (city,)).fetchone()
        cid = row["id"] if row else db.insert(
            conn, "INSERT INTO cities (name, created_at) VALUES (?, ?)", (city, db.now()))
        for campus in campuses:
            conn.execute(
                "UPDATE campuses SET city_id = ? WHERE name = ? AND city_id IS NULL",
                (cid, campus))


def _seed_courses(conn):
    """Seed every distinct course value on students under the default campuses, so
    each existing student's course validates against its campus's course list."""
    courses = [r["v"] for r in conn.execute(
        "SELECT DISTINCT application_course AS v FROM students "
        "WHERE application_course IS NOT NULL AND application_course <> ''").fetchall()]
    for campus in _SEED_COURSE_CAMPUSES:
        crow = conn.execute("SELECT id FROM campuses WHERE name = ?", (campus,)).fetchone()
        if not crow:
            continue
        for name in courses:
            name = (name or "").strip()
            if name and not conn.execute(
                    "SELECT 1 FROM courses WHERE campus_id = ? AND name = ?",
                    (crow["id"], name)).fetchone():
                conn.execute(
                    "INSERT INTO courses (campus_id, name, created_at) VALUES (?, ?, ?)",
                    (crow["id"], name, db.now()))


def _seed_agm_campuses(conn):
    """Bind every existing AGM to the default campuses (where the sample
    admissions live) so existing students pass the campus-binding validation."""
    camp_ids = [r["id"] for r in conn.execute(
        "SELECT id FROM campuses WHERE name IN ('NORTHVALE DS', 'NORTHVALE HOSTEL')").fetchall()]
    for a in conn.execute("SELECT id FROM agms").fetchall():
        for cid in camp_ids:
            if not conn.execute(
                    "SELECT 1 FROM agm_campuses WHERE agm_id = ? AND campus_id = ?",
                    (a["id"], cid)).fetchone():
                conn.execute(
                    "INSERT INTO agm_campuses (agm_id, campus_id) VALUES (?, ?)",
                    (a["id"], cid))


def _table_exists(conn, name):
    """True when a table exists in the app's `public` schema (avoids matching the
    Supabase `auth.*` tables of the same bare name)."""
    return bool(conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_name = ?", (name,)).fetchone())


def _seed_city_bindings(conn):
    """SCHEMA_VERSION 11: move the binding layer up from campus to CITY.

    * AGMs: backfill `agms.city_id` from `agm_campuses`. Every AGM is single-city,
      so its campus set collapses to one city (MIN is that one value). Only fills
      NULLs — a city later chosen in the UI is never clobbered and re-runs no-op.
    * Users: copy `user_campuses` bindings up to `user_cities` (each campus's city).
      `ON CONFLICT DO NOTHING` keeps it idempotent.

    The superseded tables are read only if they still exist (a brand-new database
    never created them and has nothing to migrate)."""
    if _table_exists(conn, "agm_campuses"):
        conn.execute(
            "UPDATE agms SET city_id = sub.city_id FROM ("
            "  SELECT ac.agm_id AS agm_id, MIN(c.city_id) AS city_id"
            "  FROM agm_campuses ac JOIN campuses c ON c.id = ac.campus_id"
            "  WHERE c.city_id IS NOT NULL GROUP BY ac.agm_id) sub "
            "WHERE agms.id = sub.agm_id AND agms.city_id IS NULL")
    if _table_exists(conn, "user_campuses"):
        conn.execute(
            "INSERT INTO user_cities (user_id, city_id) "
            "SELECT DISTINCT uc.user_id, c.city_id "
            "FROM user_campuses uc JOIN campuses c ON c.id = uc.campus_id "
            "WHERE c.city_id IS NOT NULL "
            "ON CONFLICT (user_id, city_id) DO NOTHING")


def _migrate_role_menus(conn):
    """SCHEMA_VERSION 7: the analytics screens became their own modules. Grant
    View on them to every role that could already see the student data (had
    `students` in its menu), so the upgrade preserves the current sidebar."""
    for r in conn.execute("SELECT key, menu FROM roles").fetchall():
        menu = [m for m in (r["menu"] or "").split(",") if m]
        if "students" not in menu:
            continue
        changed = False
        for mod in _V7_STUDENT_DATA_MODULES:
            if mod not in menu:
                menu.append(mod)
                changed = True
        if changed:
            conn.execute("UPDATE roles SET menu = ? WHERE key = ?",
                         (",".join(menu), r["key"]))


def seed_admin(conn):
    password = secrets.token_urlsafe(12)
    conn.execute(
        "INSERT INTO users (username, full_name, role, password_hash, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        ("admin", "Administrator", "admin", security.hash_password(password), db.now()))
    conn.commit()
    print("=" * 64)
    print("  Admissions Ledger first-run: created the initial administrator.")
    print("    username: admin")
    print(f"    password: {password}")
    print("  Sign in and change this password immediately (Profile → password).")
    print("=" * 64, flush=True)
