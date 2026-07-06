"""
The recruiting org: the ``cities`` / ``campuses`` / ``courses`` / ``agms`` /
``execs`` tables — the managed lists behind every student's campus, AGM, marketing
exec and course.

Hierarchy:
  * **City → Campus → Course.** A city owns campuses; a campus owns its course
    list. A student picks a campus; its city is derived, and its course must be one
    of that campus's courses.
  * **City-bound AGMs** (SCHEMA_VERSION 11). An AGM serves exactly ONE city
    (``agms.city_id``), covering all that city's campuses; it has 0..n **marketing
    execs** (own-exec when none). Execs inherit their AGM's city, so a student's AGM
    must serve the city of the student's campus. (Superseded the M:N ``agm_campuses``.)

Students reference campus / AGM / exec / course by *name* (mirroring the original
free-text ``agm`` column), so a rename here **cascades** to the matching student
rows. Deletes are blocked while anything still references the row.

All SQL for this domain lives here; the access decisions live in
``app.endpoints.org`` / ``app.permissions``.
"""

from app import db


def _name(s):
    return (s or "").strip()


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------
# Reads
# --------------------------------------------------------------------------

# All readers below take an optional `only` = a list of campus NAMES (the
# campus-bound-user scope). None ⇒ every campus (today's behaviour). When given,
# each list is trimmed to those campuses / the AGMs serving them.

def campus_names(only=None):
    where, params = "", ()
    if only is not None:
        where, params = " WHERE name = ANY(?)", (list(only),)
    with db.connect() as conn:
        return [r["name"] for r in conn.execute(
            f"SELECT name FROM campuses{where} ORDER BY name", params).fetchall()]


def city_names(only=None):
    if only is None:
        with db.connect() as conn:
            return [r["name"] for r in conn.execute(
                "SELECT name FROM cities ORDER BY name").fetchall()]
    # Scoped: only the cities that contain an in-scope campus.
    with db.connect() as conn:
        return [r["name"] for r in conn.execute(
            "SELECT DISTINCT ci.name AS name FROM cities ci "
            "JOIN campuses c ON c.city_id = ci.id WHERE c.name = ANY(?) "
            "ORDER BY ci.name", (list(only),)).fetchall()]


def campus_city_map(only=None):
    """``{campus_name: city_name}`` (campuses with no city are omitted)."""
    where, params = "", ()
    if only is not None:
        where, params = " WHERE c.name = ANY(?)", (list(only),)
    with db.connect() as conn:
        return {r["campus"]: r["city"] for r in conn.execute(
            "SELECT c.name AS campus, ci.name AS city "
            "FROM campuses c JOIN cities ci ON ci.id = c.city_id" + where,
            params).fetchall()}


def campus_courses_map(only=None):
    """``{campus_name: [course_name, ...]}`` for the student-form course dropdown."""
    where, params = "", ()
    if only is not None:
        where, params = " WHERE c.name = ANY(?)", (list(only),)
    out = {}
    with db.connect() as conn:
        for r in conn.execute(
                "SELECT c.name AS campus, co.name AS course "
                "FROM courses co JOIN campuses c ON c.id = co.campus_id" + where +
                " ORDER BY c.name, co.name", params).fetchall():
            out.setdefault(r["campus"], []).append(r["course"])
    return out


def campus_agms_map(only=None):
    """``{campus_name: [agm_name, ...]}`` — the AGMs serving each campus. AGMs are
    city-bound (one city each), so a campus's AGMs are those whose `city_id` matches
    the campus's city."""
    where, params = "", ()
    if only is not None:
        where, params = " WHERE c.name = ANY(?)", (list(only),)
    out = {}
    with db.connect() as conn:
        for r in conn.execute(
                "SELECT c.name AS campus, a.name AS agm "
                "FROM campuses c JOIN agms a ON a.city_id = c.city_id" + where +
                " ORDER BY c.name, a.name", params).fetchall():
            out.setdefault(r["campus"], []).append(r["agm"])
    return out


def _scoped_agm_ids(conn, only):
    """ids of the AGMs whose city contains an in-scope campus (helper for scoped
    reads). `only` is a list of campus NAMES (the caller's expanded city scope)."""
    return [r["id"] for r in conn.execute(
        "SELECT DISTINCT a.id AS id FROM agms a "
        "JOIN campuses c ON c.city_id = a.city_id "
        "WHERE c.name = ANY(?) ORDER BY a.id", (list(only),)).fetchall()]


def agm_names(only=None):
    if only is None:
        with db.connect() as conn:
            return [r["name"] for r in conn.execute(
                "SELECT name FROM agms ORDER BY name").fetchall()]
    with db.connect() as conn:
        return [r["name"] for r in conn.execute(
            "SELECT DISTINCT a.name AS name FROM agms a "
            "JOIN campuses c ON c.city_id = a.city_id WHERE c.name = ANY(?) "
            "ORDER BY a.name", (list(only),)).fetchall()]


def execs_by_agm(only=None):
    """``{agm_name: [exec_name, ...]}`` for every AGM (empty list when none).
    Scoped ⇒ only AGMs whose city contains an in-scope campus."""
    out = {}
    with db.connect() as conn:
        if only is None:
            agms = conn.execute("SELECT id, name FROM agms ORDER BY name").fetchall()
        else:
            agms = conn.execute(
                "SELECT DISTINCT a.id AS id, a.name AS name FROM agms a "
                "JOIN campuses c ON c.city_id = a.city_id WHERE c.name = ANY(?) "
                "ORDER BY a.name", (list(only),)).fetchall()
        for a in agms:
            out[a["name"]] = [e["name"] for e in conn.execute(
                "SELECT name FROM execs WHERE agm_id = ? ORDER BY name",
                (a["id"],)).fetchall()]
    return out


def org_tree(only=None):
    """The full Manage-Org payload: cities, campuses (each with city + course list)
    and AGMs (each with their campuses + execs). Scoped ⇒ only the in-scope
    campuses, the cities that contain them, and the AGMs serving them."""
    with db.connect() as conn:
        if only is None:
            campus_rows = conn.execute(
                "SELECT id, name, city_id FROM campuses ORDER BY name").fetchall()
            agm_rows = conn.execute(
                "SELECT id, name, city_id FROM agms ORDER BY name").fetchall()
        else:
            campus_rows = conn.execute(
                "SELECT id, name, city_id FROM campuses WHERE name = ANY(?) "
                "ORDER BY name", (list(only),)).fetchall()
            agm_ids = _scoped_agm_ids(conn, only)
            agm_rows = [conn.execute("SELECT id, name, city_id FROM agms WHERE id = ?",
                                     (aid,)).fetchone() for aid in agm_ids]

        city_ids = {c["city_id"] for c in campus_rows if c["city_id"] is not None}
        if only is None:
            cities = [{"id": r["id"], "name": r["name"]} for r in conn.execute(
                "SELECT id, name FROM cities ORDER BY name").fetchall()]
        else:
            cities = [{"id": r["id"], "name": r["name"]} for r in conn.execute(
                "SELECT id, name FROM cities ORDER BY name").fetchall()
                if r["id"] in city_ids]

        campuses = []
        for c in campus_rows:
            courses = [{"id": co["id"], "name": co["name"]} for co in conn.execute(
                "SELECT id, name FROM courses WHERE campus_id = ? ORDER BY name",
                (c["id"],)).fetchall()]
            campuses.append({"id": c["id"], "name": c["name"],
                             "city_id": c["city_id"], "courses": courses})

        agms = []
        for a in agm_rows:
            execs = [{"id": e["id"], "name": e["name"]} for e in conn.execute(
                "SELECT id, name FROM execs WHERE agm_id = ? ORDER BY name",
                (a["id"],)).fetchall()]
            agms.append({"id": a["id"], "name": a["name"],
                         "city_id": a["city_id"], "execs": execs})
    return {"cities": cities, "campuses": campuses, "agms": agms}


def expenditure_tree(only=None):
    """AGM teams with each exec's `total_amount` + `target` and the AGM's `is_field`
    flag, for the Expenditure screen. `is_field` = 1 marks a field admission AGM
    (Tab B); `total_amount` is the recruiter's disbursement and `target` the
    admission target, both from the PRO+STAFF sheet (nullable until loaded).
    Admission counts are joined client-side from the students payload, so no
    student SQL here. Each AGM also carries its `city` name (AGMs are city-bound),
    so the dashboards can offer a per-city filter. Scoped ⇒ only AGMs whose city
    contains an in-scope campus."""
    with db.connect() as conn:
        if only is None:
            agm_rows = conn.execute(
                "SELECT a.id AS id, a.name AS name, a.is_field AS is_field, "
                "a.rent AS rent, ci.name AS city FROM agms a "
                "LEFT JOIN cities ci ON ci.id = a.city_id "
                "ORDER BY a.name").fetchall()
        else:
            agm_rows = conn.execute(
                "SELECT DISTINCT a.id AS id, a.name AS name, a.is_field AS is_field, "
                "a.rent AS rent, ci.name AS city FROM agms a "
                "JOIN campuses c ON c.city_id = a.city_id "
                "LEFT JOIN cities ci ON ci.id = a.city_id "
                "WHERE c.name = ANY(?) ORDER BY a.name", (list(only),)).fetchall()
        out = []
        for a in agm_rows:
            execs = [{"id": e["id"], "name": e["name"],
                      "total_amount": e["total_amount"], "target": e["target"],
                      "salary": e["salary"], "gen_exp": e["gen_exp"],
                      "incentive": e["incentive"], "gift": e["gift"]}
                     for e in conn.execute(
                         "SELECT id, name, total_amount, target, salary, gen_exp, "
                         "incentive, gift FROM execs "
                         "WHERE agm_id = ? ORDER BY name", (a["id"],)).fetchall()]
            out.append({"name": a["name"], "is_field": bool(a["is_field"]),
                        "city": a["city"], "rent": a["rent"], "execs": execs})
    return out


# --------------------------------------------------------------------------
# Scope resolvers for the org write guards: the campus NAME(s) an org item
# touches, so the endpoint can require them ⊆ the caller's campus scope.
# --------------------------------------------------------------------------

def agm_campus_names(agm_id):
    """The campus NAMES an AGM serves = every campus of its city (city-bound). Used
    by the org write-guards to keep an AGM within the caller's campus scope."""
    with db.connect() as conn:
        return [r["name"] for r in conn.execute(
            "SELECT c.name AS name FROM agms a "
            "JOIN campuses c ON c.city_id = a.city_id WHERE a.id = ?",
            (_int(agm_id),)).fetchall()]


def city_campus_names(city_id):
    """The campus NAMES in a city (for the AGM create/move write-guards)."""
    cid = _int(city_id)
    if cid is None:
        return []
    with db.connect() as conn:
        return [r["name"] for r in conn.execute(
            "SELECT name FROM campuses WHERE city_id = ?", (cid,)).fetchall()]


def course_campus_name(course_id):
    with db.connect() as conn:
        row = conn.execute(
            "SELECT c.name AS name FROM courses co "
            "JOIN campuses c ON c.id = co.campus_id WHERE co.id = ?",
            (_int(course_id),)).fetchone()
        return row["name"] if row else None


def exec_campus_names(exec_id):
    """The campuses an exec's AGM serves = every campus of the AGM's city (execs
    inherit their city through their AGM)."""
    with db.connect() as conn:
        return [r["name"] for r in conn.execute(
            "SELECT c.name AS name FROM execs e "
            "JOIN agms a ON a.id = e.agm_id "
            "JOIN campuses c ON c.city_id = a.city_id WHERE e.id = ?",
            (_int(exec_id),)).fetchall()]


def campus_name_by_id(campus_id):
    with db.connect() as conn:
        row = conn.execute("SELECT name FROM campuses WHERE id = ?",
                           (_int(campus_id),)).fetchone()
        return row["name"] if row else None


# --------------------------------------------------------------------------
# Cities (own campuses; a campus's city is derived for the student/filter views)
# --------------------------------------------------------------------------

def create_city(name):
    name = _name(name)
    if not name:
        return False, "City name is required.", None
    with db.connect() as conn:
        try:
            cid = db.insert(conn,
                "INSERT INTO cities (name, created_at) VALUES (?, ?)",
                (name, db.now()))
            conn.commit()
        except db.INTEGRITY_ERRORS:
            return False, "A city with that name already exists.", None
    return True, "City added.", cid


def rename_city(city_id, name):
    name = _name(name)
    if not name:
        return False, "City name is required."
    with db.connect() as conn:
        if not conn.execute("SELECT 1 FROM cities WHERE id = ?",
                            (_int(city_id),)).fetchone():
            return False, "City not found."
        try:
            conn.execute("UPDATE cities SET name = ? WHERE id = ?",
                         (name, _int(city_id)))
            conn.commit()
        except db.INTEGRITY_ERRORS:
            conn.rollback()
            return False, "A city with that name already exists."
    return True, "City renamed."


def delete_city(city_id):
    with db.connect() as conn:
        if not conn.execute("SELECT 1 FROM cities WHERE id = ?",
                            (_int(city_id),)).fetchone():
            return False, "City not found."
        used = conn.execute("SELECT COUNT(*) AS c FROM campuses WHERE city_id = ?",
                           (_int(city_id),)).fetchone()["c"]
        if used:
            return False, f"{used} campus(es) are in this city. Reassign them first."
        conn.execute("DELETE FROM cities WHERE id = ?", (_int(city_id),))
        conn.commit()
    return True, "City deleted."


# --------------------------------------------------------------------------
# Campuses
# --------------------------------------------------------------------------

def create_campus(name, city_id=None):
    name = _name(name)
    if not name:
        return False, "Campus name is required.", None
    city_id = _int(city_id)
    with db.connect() as conn:
        if city_id is not None and not conn.execute(
                "SELECT 1 FROM cities WHERE id = ?", (city_id,)).fetchone():
            return False, "Unknown city.", None
        try:
            cid = db.insert(conn,
                "INSERT INTO campuses (name, city_id, created_at) VALUES (?, ?, ?)",
                (name, city_id, db.now()))
            conn.commit()
        except db.INTEGRITY_ERRORS:
            return False, "A campus with that name already exists.", None
    return True, "Campus added.", cid


def set_campus_city(campus_id, city_id):
    """Move a campus to a city (or clear it with a null/blank city_id)."""
    city_id = _int(city_id)
    with db.connect() as conn:
        if not conn.execute("SELECT 1 FROM campuses WHERE id = ?",
                            (_int(campus_id),)).fetchone():
            return False, "Campus not found."
        if city_id is not None and not conn.execute(
                "SELECT 1 FROM cities WHERE id = ?", (city_id,)).fetchone():
            return False, "Unknown city."
        conn.execute("UPDATE campuses SET city_id = ? WHERE id = ?",
                     (city_id, _int(campus_id)))
        conn.commit()
    return True, "Campus moved."


def rename_campus(campus_id, name):
    name = _name(name)
    if not name:
        return False, "Campus name is required."
    with db.connect() as conn:
        row = conn.execute("SELECT name FROM campuses WHERE id = ?",
                           (int(campus_id),)).fetchone()
        if not row:
            return False, "Campus not found."
        old = row["name"]
        try:
            conn.execute("UPDATE campuses SET name = ? WHERE id = ?",
                         (name, int(campus_id)))
            conn.execute("UPDATE students SET campus = ? WHERE campus = ?",
                         (name, old))
            conn.commit()
        except db.INTEGRITY_ERRORS:
            conn.rollback()
            return False, "A campus with that name already exists."
    return True, "Campus renamed."


def delete_campus(campus_id):
    with db.connect() as conn:
        row = conn.execute("SELECT name FROM campuses WHERE id = ?",
                           (int(campus_id),)).fetchone()
        if not row:
            return False, "Campus not found."
        used = conn.execute("SELECT COUNT(*) AS c FROM students WHERE campus = ?",
                           (row["name"],)).fetchone()["c"]
        if used:
            return False, f"{used} student(s) are in this campus. Reassign them first."
        conn.execute("DELETE FROM campuses WHERE id = ?", (int(campus_id),))
        conn.commit()
    return True, "Campus deleted."


# --------------------------------------------------------------------------
# Courses (each belongs to one campus; renames cascade to that campus's students)
# --------------------------------------------------------------------------

def create_course(campus_id, name):
    name = _name(name)
    if not name:
        return False, "Course name is required.", None
    with db.connect() as conn:
        if not conn.execute("SELECT 1 FROM campuses WHERE id = ?",
                            (_int(campus_id),)).fetchone():
            return False, "Campus not found.", None
        try:
            cid = db.insert(conn,
                "INSERT INTO courses (campus_id, name, created_at) VALUES (?, ?, ?)",
                (_int(campus_id), name, db.now()))
            conn.commit()
        except db.INTEGRITY_ERRORS:
            return False, "This campus already offers that course.", None
    return True, "Course added.", cid


def rename_course(course_id, name):
    name = _name(name)
    if not name:
        return False, "Course name is required."
    with db.connect() as conn:
        row = conn.execute(
            "SELECT co.name AS name, c.name AS campus FROM courses co "
            "JOIN campuses c ON c.id = co.campus_id WHERE co.id = ?",
            (_int(course_id),)).fetchone()
        if not row:
            return False, "Course not found."
        old = row["name"]
        try:
            conn.execute("UPDATE courses SET name = ? WHERE id = ?",
                         (name, _int(course_id)))
            # Cascade only to this campus's students naming the old course.
            conn.execute(
                "UPDATE students SET application_course = ? "
                "WHERE application_course = ? AND campus = ?",
                (name, old, row["campus"]))
            conn.commit()
        except db.INTEGRITY_ERRORS:
            conn.rollback()
            return False, "This campus already offers that course."
    return True, "Course renamed."


def delete_course(course_id):
    with db.connect() as conn:
        row = conn.execute(
            "SELECT co.name AS name, c.name AS campus FROM courses co "
            "JOIN campuses c ON c.id = co.campus_id WHERE co.id = ?",
            (_int(course_id),)).fetchone()
        if not row:
            return False, "Course not found."
        used = conn.execute(
            "SELECT COUNT(*) AS c FROM students "
            "WHERE application_course = ? AND campus = ?",
            (row["name"], row["campus"])).fetchone()["c"]
        if used:
            return False, f"{used} student(s) in this campus take this course. Reassign them first."
        conn.execute("DELETE FROM courses WHERE id = ?", (_int(course_id),))
        conn.commit()
    return True, "Course deleted."


# --------------------------------------------------------------------------
# AGMs (campus-bound: each serves 1..n campuses)
# --------------------------------------------------------------------------

def create_agm(name, city_id=None):
    name = _name(name)
    if not name:
        return False, "AGM name is required.", None
    cid = _int(city_id)
    with db.connect() as conn:
        if cid is not None and not conn.execute(
                "SELECT 1 FROM cities WHERE id = ?", (cid,)).fetchone():
            return False, "Unknown city.", None
        try:
            aid = db.insert(conn,
                "INSERT INTO agms (name, city_id, created_at) VALUES (?, ?, ?)",
                (name, cid, db.now()))
            conn.commit()
        except db.INTEGRITY_ERRORS:
            return False, "An AGM with that name already exists.", None
    return True, "AGM added.", aid


def set_agm_city(agm_id, city_id):
    """Set the single city an AGM serves. `city_id` None ⇒ unassigned (the AGM then
    serves no campus and won't appear on the student form)."""
    aid, cid = _int(agm_id), _int(city_id)
    with db.connect() as conn:
        if not conn.execute("SELECT 1 FROM agms WHERE id = ?", (aid,)).fetchone():
            return False, "AGM not found."
        if cid is not None and not conn.execute(
                "SELECT 1 FROM cities WHERE id = ?", (cid,)).fetchone():
            return False, "Unknown city."
        conn.execute("UPDATE agms SET city_id = ? WHERE id = ?", (cid, aid))
        conn.commit()
    return True, "AGM city updated."


def rename_agm(agm_id, name):
    name = _name(name)
    if not name:
        return False, "AGM name is required."
    with db.connect() as conn:
        row = conn.execute("SELECT name FROM agms WHERE id = ?",
                           (int(agm_id),)).fetchone()
        if not row:
            return False, "AGM not found."
        old = row["name"]
        try:
            conn.execute("UPDATE agms SET name = ? WHERE id = ?",
                         (name, int(agm_id)))
            conn.execute("UPDATE students SET agm = ? WHERE agm = ?", (name, old))
            conn.commit()
        except db.INTEGRITY_ERRORS:
            conn.rollback()
            return False, "An AGM with that name already exists."
    return True, "AGM renamed."


def delete_agm(agm_id):
    with db.connect() as conn:
        row = conn.execute("SELECT name FROM agms WHERE id = ?",
                           (int(agm_id),)).fetchone()
        if not row:
            return False, "AGM not found."
        used = conn.execute("SELECT COUNT(*) AS c FROM students WHERE agm = ?",
                           (row["name"],)).fetchone()["c"]
        if used:
            return False, f"{used} admission(s) belong to this AGM. Reassign them first."
        # execs cascade via the FK, but be explicit so it works without ON DELETE.
        conn.execute("DELETE FROM execs WHERE agm_id = ?", (int(agm_id),))
        conn.execute("DELETE FROM agms WHERE id = ?", (int(agm_id),))
        conn.commit()
    return True, "AGM deleted."


# --------------------------------------------------------------------------
# Marketing execs (each under exactly one AGM)
# --------------------------------------------------------------------------

def create_exec(agm_id, name):
    name = _name(name)
    if not name:
        return False, "Exec name is required.", None
    with db.connect() as conn:
        if not conn.execute("SELECT 1 FROM agms WHERE id = ?",
                            (int(agm_id),)).fetchone():
            return False, "AGM not found.", None
        try:
            eid = db.insert(conn,
                "INSERT INTO execs (agm_id, name, created_at) VALUES (?, ?, ?)",
                (int(agm_id), name, db.now()))
            conn.commit()
        except db.INTEGRITY_ERRORS:
            return False, "This AGM already has an exec with that name.", None
    return True, "Marketing exec added.", eid


def rename_exec(exec_id, name):
    name = _name(name)
    if not name:
        return False, "Exec name is required."
    with db.connect() as conn:
        row = conn.execute(
            "SELECT e.name AS name, e.agm_id AS agm_id, a.name AS agm "
            "FROM execs e JOIN agms a ON a.id = e.agm_id WHERE e.id = ?",
            (int(exec_id),)).fetchone()
        if not row:
            return False, "Marketing exec not found."
        old = row["name"]
        try:
            conn.execute("UPDATE execs SET name = ? WHERE id = ?",
                         (name, int(exec_id)))
            # Cascade only to this AGM's students (exec names are unique per AGM).
            conn.execute(
                "UPDATE students SET marketing_exec = ? "
                "WHERE marketing_exec = ? AND agm = ?",
                (name, old, row["agm"]))
            conn.commit()
        except db.INTEGRITY_ERRORS:
            conn.rollback()
            return False, "This AGM already has an exec with that name."
    return True, "Marketing exec renamed."


def delete_exec(exec_id):
    with db.connect() as conn:
        row = conn.execute(
            "SELECT e.name AS name, a.name AS agm "
            "FROM execs e JOIN agms a ON a.id = e.agm_id WHERE e.id = ?",
            (int(exec_id),)).fetchone()
        if not row:
            return False, "Marketing exec not found."
        used = conn.execute(
            "SELECT COUNT(*) AS c FROM students WHERE marketing_exec = ? AND agm = ?",
            (row["name"], row["agm"])).fetchone()["c"]
        if used:
            return False, f"{used} admission(s) name this exec. Reassign them first."
        conn.execute("DELETE FROM execs WHERE id = ?", (int(exec_id),))
        conn.commit()
    return True, "Marketing exec deleted."


# --------------------------------------------------------------------------
# Used by the students data layer to ensure-and-validate on import
# --------------------------------------------------------------------------

def ensure_campus(conn, name):
    """Insert a campus by name if missing (admin-only import path). No-op blank."""
    name = _name(name)
    if not name:
        return
    if not conn.execute("SELECT 1 FROM campuses WHERE name = ?", (name,)).fetchone():
        conn.execute("INSERT INTO campuses (name, created_at) VALUES (?, ?)",
                     (name, db.now()))


def ensure_agm(conn, name):
    name = _name(name)
    if not name:
        return None
    row = conn.execute("SELECT id FROM agms WHERE name = ?", (name,)).fetchone()
    if row:
        return row["id"]
    return db.insert(conn, "INSERT INTO agms (name, created_at) VALUES (?, ?)",
                     (name, db.now()))


def ensure_agm_city(conn, agm_id, campus_name):
    """Set an AGM's city from a campus's city if the AGM has none yet (import path),
    so imported admissions satisfy the city-binding validation. Never overwrites an
    AGM that already serves a city."""
    campus_name = _name(campus_name)
    if not agm_id or not campus_name:
        return
    crow = conn.execute("SELECT city_id FROM campuses WHERE name = ?",
                       (campus_name,)).fetchone()
    if crow and crow["city_id"] is not None:
        conn.execute("UPDATE agms SET city_id = ? WHERE id = ? AND city_id IS NULL",
                     (crow["city_id"], agm_id))


def ensure_course(conn, campus_name, name):
    """Insert a course under a campus (by name) if missing (import path)."""
    campus_name, name = _name(campus_name), _name(name)
    if not campus_name or not name:
        return
    crow = conn.execute("SELECT id FROM campuses WHERE name = ?",
                       (campus_name,)).fetchone()
    if crow and not conn.execute(
            "SELECT 1 FROM courses WHERE campus_id = ? AND name = ?",
            (crow["id"], name)).fetchone():
        conn.execute("INSERT INTO courses (campus_id, name, created_at) VALUES (?, ?, ?)",
                     (crow["id"], name, db.now()))


def ensure_exec(conn, agm_id, name):
    name = _name(name)
    if not name or not agm_id:
        return
    if not conn.execute("SELECT 1 FROM execs WHERE agm_id = ? AND name = ?",
                        (agm_id, name)).fetchone():
        conn.execute("INSERT INTO execs (agm_id, name, created_at) VALUES (?, ?, ?)",
                     (agm_id, name, db.now()))
