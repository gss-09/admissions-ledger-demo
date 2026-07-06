"""
Admissions (the `students` table): the full ledger read, distinct dropdown
values, add / update / delete, the dashboard summary, and a non-destructive
CSV merge. Column names mirror the original SQLite app so the migration loads
straight across.
"""

from app import db
from app.config import DEFAULT_STATUS
from app.data import org as org_db

# Columns returned to the front-end (status_raw / hidden / registered_* stay
# internal). This literal list is the only "dynamic" part of the SELECT.
_PUBLIC_COLS = (
    "id, appn_no, student_name, father_name, grp, application_course, "
    "mobile1, mobile2, agm, marketing_exec, campus, final_fee, hostel, "
    "status_category, reported_date"
)


def _digits(s):
    """Keep only the digits of a phone value (or None)."""
    return "".join(ch for ch in (s or "") if ch.isdigit()) or None


def _fee(v):
    """Parse a whole-rupee final fee → int or None. Keeps digits only, so
    '45000', '₹45,000' and '45,000' all yield 45000; blank → None."""
    digits = "".join(ch for ch in str("" if v is None else v) if ch.isdigit())
    return int(digits) if digits else None


def _hostel(v):
    """Normalise a hostel value to 'AC' / 'NON-AC' / None. Accepts the loose
    spellings that turn up in source data ('A/C', 'NON-A/C', 'Non AC', …);
    anything else (including a bare '-') is treated as unset."""
    s = (v or "").strip().upper().replace("/", "").replace(" ", "")
    if not s:
        return None
    if s.startswith("NON"):
        return "NON-AC"
    if "AC" in s:
        return "AC"
    return None


def _name(s):
    return (s or "").strip().upper() or None


def _resolve_org(conn, d):
    """Validate a student's campus / AGM / exec / course against the managed lists,
    using the caller's connection. Enforces the City→Campus→Course hierarchy and
    city-bound AGMs server-side:

      * campus must be a known campus,
      * AGM must be a known AGM that SERVES that campus — i.e. the AGM's ``city_id``
        equals the campus's ``city_id`` (city-bound AGMs),
      * if that AGM has execs, the marketing exec is required and must be one of
        them; if it has none, the exec is cleared (the AGM acts as its own exec),
      * the course, when given, must be offered at that campus (``courses``).

    Returns ``(ok, message, agm, marketing_exec, campus)``. (The course is not
    rewritten here — it is stored straight from ``d`` by the caller — but it is
    validated against the campus.)
    """
    agm = (d.get("agm") or "").strip()
    campus = (d.get("campus") or "").strip()
    me = (d.get("marketing_exec") or "").strip()
    course = (d.get("application_course") or "").strip()

    if not campus:
        return False, "Campus is required.", None, None, None
    crow = conn.execute("SELECT id, city_id FROM campuses WHERE name = ?",
                        (campus,)).fetchone()
    if not crow:
        return False, "Unknown campus.", None, None, None

    if not agm:
        return False, "AGM is required.", None, None, None
    arow = conn.execute("SELECT id, city_id FROM agms WHERE name = ?", (agm,)).fetchone()
    if not arow:
        return False, "Unknown AGM.", None, None, None
    # City-bound AGMs: the AGM serves the student's campus iff they share a city.
    if arow["city_id"] is None or arow["city_id"] != crow["city_id"]:
        return False, "That AGM doesn't serve this campus.", None, None, None

    execs = [e["name"] for e in conn.execute(
        "SELECT name FROM execs WHERE agm_id = ?", (arow["id"],)).fetchall()]
    if execs:
        if not me:
            return False, "Marketing exec is required for this AGM.", None, None, None
        if me not in execs:
            return False, "That marketing exec is not under the selected AGM.", \
                None, None, None
    else:
        me = ""   # AGM has no execs → it is its own exec

    if course and not conn.execute(
            "SELECT 1 FROM courses WHERE campus_id = ? AND name = ?",
            (crow["id"], course)).fetchone():
        return False, "That course isn't offered at this campus.", None, None, None

    return True, "", agm, (me or None), campus


def list_all(campus_names=None):
    """Every student, ordered by AGM then name (the directory + overview feed).
    When `campus_names` is a list, only those campuses' rows are returned (the
    campus-bound-user scope); None ⇒ all campuses."""
    where, params = "", ()
    if campus_names is not None:
        where, params = " WHERE campus = ANY(?)", (list(campus_names),)
    with db.connect() as conn:
        rows = conn.execute(
            f"SELECT {_PUBLIC_COLS} FROM students{where} "
            f"ORDER BY agm, LOWER(student_name)", params
        ).fetchall()
    return [dict(r) for r in rows]


def distinct_meta(campus_names=None):
    """Dropdown/filter metadata for the Admissions screen and the add/edit forms:
    the managed AGM, exec and campus lists, plus the distinct course/group values
    still kept as free text. Column names are literals, never user input.

    When `campus_names` is given (a campus-bound user), every list is trimmed to
    those campuses so the screen only ever offers reachable options."""
    scoped = campus_names is not None
    cfilter = " AND campus = ANY(?)" if scoped else ""
    cparams = (list(campus_names),) if scoped else ()
    with db.connect() as conn:
        def col(name):
            return [r["v"] for r in conn.execute(
                f"SELECT DISTINCT {name} AS v FROM students "
                f"WHERE {name} IS NOT NULL AND {name} <> ''{cfilter} ORDER BY {name}",
                cparams
            ).fetchall()]
        courses, groups = col("application_course"), col("grp")
    return {"agms": org_db.agm_names(campus_names), "execs": org_db.execs_by_agm(campus_names),
            "campuses": org_db.campus_names(campus_names),
            "courses": courses, "groups": groups,
            # City→Campus→Course hierarchy + campus-bound AGMs, for the student
            # form cascade (campus drives AGM/exec/course; city is derived) and the
            # City filter. campus_courses/campus_agms key the dependent dropdowns.
            "cities": org_db.city_names(campus_names),
            "campus_city": org_db.campus_city_map(campus_names),
            "campus_courses": org_db.campus_courses_map(campus_names),
            "campus_agms": org_db.campus_agms_map(campus_names)}


def create_student(d, registered_by):
    """Add one admission. `d` is the raw form dict from the client."""
    name = _name(d.get("student_name"))
    if not name:
        return False, "Student name is required.", None
    status = d.get("status_category") or DEFAULT_STATUS
    rep = d.get("reported_date") if status == "REPORTED" else None
    with db.connect() as conn:
        ok, msg, agm, me, campus = _resolve_org(conn, d)
        if not ok:
            return False, msg, None
        sid = db.insert(conn,
            "INSERT INTO students (appn_no, student_name, father_name, grp, "
            "application_course, mobile1, mobile2, agm, marketing_exec, campus, "
            "final_fee, hostel, status_raw, status_category, reported_date, hidden, "
            "registered_by, registered_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
            ((d.get("appn_no") or "").strip() or None, name,
             _name(d.get("father_name")), d.get("grp"),
             d.get("application_course"), _digits(d.get("mobile1")),
             _digits(d.get("mobile2")), agm, me, campus, _fee(d.get("final_fee")),
             _hostel(d.get("hostel")),
             status, status, rep, registered_by, db.now()))
        conn.commit()
    return True, "Admission added.", sid


def update_student(student_id, d):
    """Update every editable field the detail modal exposes (name, appn no,
    father, AGM, course, group, phones, final fee, hostel, status and reported
    date). Reported date is cleared unless status=REPORTED."""
    name = _name(d.get("student_name"))
    if not name:
        return False, "Student name is required."
    status = (d.get("status_category") or "").strip() or DEFAULT_STATUS
    rep = d.get("reported_date") if status == "REPORTED" else None
    with db.connect() as conn:
        ok, msg, agm, me, campus = _resolve_org(conn, d)
        if not ok:
            return False, msg
        conn.execute(
            "UPDATE students SET appn_no = ?, student_name = ?, father_name = ?, "
            "grp = ?, application_course = ?, mobile1 = ?, mobile2 = ?, "
            "agm = ?, marketing_exec = ?, campus = ?, final_fee = ?, hostel = ?, "
            "status_raw = ?, status_category = ?, reported_date = ? WHERE id = ?",
            ((d.get("appn_no") or "").strip() or None, name,
             _name(d.get("father_name")), (d.get("grp") or "").strip() or None,
             (d.get("application_course") or "").strip() or None,
             _digits(d.get("mobile1")), _digits(d.get("mobile2")),
             agm, me, campus, _fee(d.get("final_fee")), _hostel(d.get("hostel")),
             status, status, rep, int(student_id)))
        conn.commit()
    return True, "Saved."


def get_student(student_id):
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM students WHERE id = ?",
                           (int(student_id),)).fetchone()
        return dict(row) if row else None


def delete_student(student_id):
    with db.connect() as conn:
        conn.execute("DELETE FROM students WHERE id = ?", (int(student_id),))
        conn.commit()
    return True, "Admission deleted."


def merge_rows(rows, registered_by):
    """Non-destructively merge `rows` (parsed from a CSV) into the students table.
    Existing students are matched by a non-blank `appn_no` and updated in place;
    everything else is inserted. Blank-name rows are skipped. Returns a summary
    ``{"added", "updated", "skipped"}``."""
    added = updated = skipped = 0
    with db.connect() as conn:
        by_adm = {}
        for s in conn.execute("SELECT id, appn_no FROM students").fetchall():
            adm = (s["appn_no"] or "").strip()
            if adm:
                by_adm.setdefault(adm, s["id"])
        for r in rows:
            name = _name(r.get("student_name") or r.get("name"))
            if not name:
                skipped += 1
                continue
            adm = (r.get("appn_no") or r.get("admission_no") or "").strip()
            father = _name(r.get("father_name") or r.get("father"))
            grp = (r.get("grp") or r.get("group") or "").strip() or None
            course = (r.get("application_course") or r.get("course") or "").strip() or None
            agm = (r.get("agm") or "").strip() or None
            me = (r.get("marketing_exec") or r.get("exec") or "").strip() or None
            campus = (r.get("campus") or "").strip() or None
            m1 = _digits(r.get("mobile1") or r.get("mobile"))
            m2 = _digits(r.get("mobile2") or r.get("whatsapp"))
            fee = _fee(r.get("final_fee") or r.get("fee"))
            hostel = _hostel(r.get("hostel"))
            status = (r.get("status_category") or r.get("status") or DEFAULT_STATUS).strip().upper()
            rep = (r.get("reported_date") or "").strip() or None
            if status != "REPORTED":
                rep = None
            # Register any new campus / AGM / exec / course the row references, so
            # the managed lists stay authoritative (bulk import is admin-only), and
            # set the AGM's city from the row's campus so the row passes org validation.
            org_db.ensure_campus(conn, campus)
            agm_id = org_db.ensure_agm(conn, agm)
            org_db.ensure_exec(conn, agm_id, me)
            org_db.ensure_agm_city(conn, agm_id, campus)
            org_db.ensure_course(conn, campus, course)
            existing = by_adm.get(adm) if adm else None
            if existing is not None:
                # Keep an existing campus/exec when the CSV leaves them blank.
                conn.execute(
                    "UPDATE students SET student_name = ?, father_name = ?, grp = ?, "
                    "application_course = ?, mobile1 = ?, mobile2 = ?, "
                    "agm = ?, marketing_exec = COALESCE(?, marketing_exec), "
                    "campus = COALESCE(?, campus), final_fee = COALESCE(?, final_fee), "
                    "hostel = COALESCE(?, hostel), "
                    "status_raw = ?, status_category = ?, reported_date = ? WHERE id = ?",
                    (name, father, grp, course, m1, m2, agm, me, campus,
                     fee, hostel, status, status, rep, existing))
                updated += 1
            else:
                new_id = db.insert(conn,
                    "INSERT INTO students (appn_no, student_name, father_name, grp, "
                    "application_course, mobile1, mobile2, agm, marketing_exec, "
                    "campus, final_fee, hostel, status_raw, status_category, reported_date, "
                    "hidden, registered_by, registered_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
                    (adm or None, name, father, grp, course, m1, m2, agm, me,
                     campus or "NORTHVALE DS", fee, hostel, status, status, rep,
                     registered_by, db.now()))
                if adm:
                    by_adm[adm] = new_id   # later rows update, never double-insert
                added += 1
        conn.commit()
    return {"added": added, "updated": updated, "skipped": skipped}
