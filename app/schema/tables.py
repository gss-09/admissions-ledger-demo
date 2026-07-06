"""All CREATE TABLE IF NOT EXISTS statements — the full table catalogue.
Run by ``init_db()`` before seeding; everything here is idempotent."""

from app import db


def create_tables(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT UNIQUE NOT NULL,
            full_name     TEXT NOT NULL,
            role          TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at    TEXT NOT NULL
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS roles (
            key      TEXT PRIMARY KEY,
            label    TEXT NOT NULL,
            menu     TEXT NOT NULL DEFAULT 'home',
            editable TEXT NOT NULL DEFAULT '',
            extras   TEXT NOT NULL DEFAULT '',
            builtin  INTEGER NOT NULL DEFAULT 0
        )
        """
    )

    # The admissions ledger. Column names mirror the original SQLite app so the
    # one-time migration loads straight across. `status_raw` keeps the original
    # imported wording; `status_category` is the normalised funnel stage.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS students (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            appn_no            TEXT,
            student_name       TEXT NOT NULL,
            father_name        TEXT,
            grp                TEXT,
            application_course TEXT,
            mobile1            TEXT,
            mobile2            TEXT,
            agm                TEXT,
            status_raw         TEXT,
            status_category    TEXT,
            reported_date      TEXT,
            hidden             INTEGER NOT NULL DEFAULT 0,
            registered_by      TEXT,
            registered_at      TEXT
        )
        """
    )

    # Two columns added in SCHEMA_VERSION 2: the campus a student reported to
    # (admin-managed list) and the marketing exec who brought them (an exec rolls
    # up to one AGM). Stored as names — matching the existing free-text `agm` — so
    # the directory/import keep working; renames cascade in app.data.org.
    student_cols = db.columns(conn, "students")
    if "campus" not in student_cols:
        conn.execute("ALTER TABLE students ADD COLUMN campus TEXT")
    if "marketing_exec" not in student_cols:
        conn.execute("ALTER TABLE students ADD COLUMN marketing_exec TEXT")

    # Added in SCHEMA_VERSION 3: the final fee agreed for a student, stored as a
    # whole-rupee integer (nullable — existing rows stay blank until set).
    if "final_fee" not in student_cols:
        conn.execute("ALTER TABLE students ADD COLUMN final_fee INTEGER")

    # Added in SCHEMA_VERSION 5: the hostel type a student opted for — 'AC' or
    # 'NON-AC' (nullable text; existing rows stay blank until set).
    if "hostel" not in student_cols:
        conn.execute("ALTER TABLE students ADD COLUMN hostel TEXT")

    # Dropped in SCHEMA_VERSION 4: the `gender` column was unreliable in the
    # source data (it mirrored campus and contradicted the names), so it is
    # removed entirely — campus already carries that distinction.
    if "gender" in student_cols:
        conn.execute("ALTER TABLE students DROP COLUMN gender")

    # The recruiting org: admin-managed campuses, AGMs, and the execs under each
    # AGM (0..n). Students reference these by name (see above).
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS campuses (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    # Added in SCHEMA_VERSION 7: a City → Campus hierarchy. Cities own campuses
    # (each campus belongs to 0..1 city via `city_id`). A student's city is always
    # DERIVED from its campus (no city column on students); the city is hidden on
    # the student form and surfaced only as a filter / grouping.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cities (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    if "city_id" not in db.columns(conn, "campuses"):
        conn.execute("ALTER TABLE campuses ADD COLUMN city_id INTEGER REFERENCES cities(id)")

    # Added in SCHEMA_VERSION 7: per-campus course lists. A course belongs to one
    # campus (same course name can exist under several campuses as separate rows).
    # Students keep the free-text `application_course`, validated against the
    # chosen campus's courses; a rename here cascades to that campus's students.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS courses (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            campus_id  INTEGER NOT NULL REFERENCES campuses(id) ON DELETE CASCADE,
            name       TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE (campus_id, name)
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agms (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS execs (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            agm_id     INTEGER NOT NULL REFERENCES agms(id) ON DELETE CASCADE,
            name       TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE (agm_id, name)
        )
        """
    )

    # Added in SCHEMA_VERSION 7: campus-bound AGMs. An AGM serves 1..n campuses
    # (many-to-many). Execs inherit their campuses THROUGH their AGM, so there is
    # no exec↔campus table. A student's AGM must serve the student's campus.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agm_campuses (
            agm_id     INTEGER NOT NULL REFERENCES agms(id) ON DELETE CASCADE,
            campus_id  INTEGER NOT NULL REFERENCES campuses(id) ON DELETE CASCADE,
            UNIQUE (agm_id, campus_id)
        )
        """
    )

    # Added in SCHEMA_VERSION 6 for the Expenditure screen: the recruiter's total
    # disbursement (salary + general expenditure + incentive + gift) from the
    # PRO+STAFF target-vs-achievement sheet, as whole rupees (nullable). And
    # `is_field` on an AGM — 1 marks a field admission AGM "whose job is just
    # admissions" (the Expenditure tab's field-only view filters on it).
    if "total_amount" not in db.columns(conn, "execs"):
        conn.execute("ALTER TABLE execs ADD COLUMN total_amount INTEGER")
    # Added in SCHEMA_VERSION 8: the recruiter's admission TARGET (TOT TARGET from
    # the PRO+STAFF sheet), a nullable whole number; a team's target is the sum of
    # its execs'. Shown alongside Admissions on the Expenditure screen.
    if "target" not in db.columns(conn, "execs"):
        conn.execute("ALTER TABLE execs ADD COLUMN target INTEGER")
    # Added in SCHEMA_VERSION 10: the FOUR component pieces of `total_amount`, so the
    # Expenditure screen can show a per-person cost breakdown (Salary / General
    # Expenditure / Incentive / Gift) under the existing per-admission table. All
    # nullable whole rupees, from the PRO+STAFF sheet (cols N/O/P/Q). The invariant
    # the UI relies on: COALESCE(salary,0)+gen_exp+incentive+gift = total_amount —
    # so for non-admission STAFF execs `salary` is NULL (their salary is not an
    # admission cost; total_amount = O+P+Q), while field execs carry the real salary.
    exec_cols = db.columns(conn, "execs")
    for col in ("salary", "gen_exp", "incentive", "gift"):
        if col not in exec_cols:
            conn.execute(f"ALTER TABLE execs ADD COLUMN {col} INTEGER")
    agm_cols = db.columns(conn, "agms")
    if "is_field" not in agm_cols:
        conn.execute("ALTER TABLE agms ADD COLUMN is_field INTEGER NOT NULL DEFAULT 0")
    # Superseded a short-lived `area` text column (lossy — one place-name couldn't
    # cover an AGM spanning two zones). Carry its flag into is_field, then drop it.
    if "area" in agm_cols:
        conn.execute("UPDATE agms SET is_field = 1 WHERE area IS NOT NULL")
        conn.execute("ALTER TABLE agms DROP COLUMN area")
    # Added in SCHEMA_VERSION 11: city-bound AGMs. An AGM now serves exactly ONE
    # city (covering ALL that city's campuses), so the binding moves up from
    # `agm_campuses` (M:N, superseded) to a single `city_id` here. Backfilled from
    # the old table in `seeds.seed_city_bindings`. `agm_campuses` is left in place
    # (vestigial) for one release rather than dropped destructively.
    if "city_id" not in agm_cols:
        conn.execute("ALTER TABLE agms ADD COLUMN city_id INTEGER REFERENCES cities(id)")
    # Added in SCHEMA_VERSION 12: per-TEAM rent for the Expenditure tab. Rent is a
    # whole-team cost (premises rent), NOT a per-exec figure, so it lives on the AGM
    # (one value per team) — nullable whole rupees, default 0. It is folded into the
    # team's Total Cost and shown as a Rent column in the cost-breakdown table for
    # admission (field) AGMs only; staff teams have no rent.
    if "rent" not in agm_cols:
        conn.execute("ALTER TABLE agms ADD COLUMN rent INTEGER DEFAULT 0")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS password_changes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            target_user_id  INTEGER,
            target_name     TEXT NOT NULL,
            target_username TEXT NOT NULL,
            actor_user_id   INTEGER,
            actor_name      TEXT NOT NULL,
            actor_username  TEXT NOT NULL,
            kind            TEXT NOT NULL DEFAULT 'reset',
            created_at      TEXT NOT NULL
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS edit_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            username    TEXT NOT NULL DEFAULT '',
            full_name   TEXT NOT NULL DEFAULT '',
            role        TEXT NOT NULL DEFAULT '',
            module      TEXT NOT NULL DEFAULT '',
            action      TEXT NOT NULL DEFAULT '',
            detail      TEXT NOT NULL DEFAULT '',
            created_at  TEXT NOT NULL
        )
        """
    )

    # Added in SCHEMA_VERSION 9: campus-bound users. A user is bound to 1..n
    # campuses (many-to-many) and may then see/edit only those campuses' data.
    # The KEY rule: rows present ⇒ bound to exactly those campuses; NO rows ⇒ all
    # campuses (org-wide). Admin is always org-wide regardless. So existing users
    # migrate with zero rows = unchanged behaviour, and a new campus is auto-visible
    # to every org-wide user with no backfill. Mirrors `agm_campuses`.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS user_campuses (
            user_id    INTEGER NOT NULL REFERENCES users(id)    ON DELETE CASCADE,
            campus_id  INTEGER NOT NULL REFERENCES campuses(id) ON DELETE CASCADE,
            UNIQUE (user_id, campus_id)
        )
        """
    )

    # Added in SCHEMA_VERSION 11: city-bound users. The user scope moves up from
    # `user_campuses` (M:N campuses, superseded) to cities — a user is bound to
    # 1..n CITIES and sees only those cities' campuses (expanded live). The KEY
    # rule is unchanged: rows present ⇒ bound to exactly those cities; NO rows ⇒
    # all cities (org-wide); admin always org-wide. Backfilled from `user_campuses`
    # in `seeds.seed_city_bindings`; the old table is left vestigial for a release.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS user_cities (
            user_id    INTEGER NOT NULL REFERENCES users(id)  ON DELETE CASCADE,
            city_id    INTEGER NOT NULL REFERENCES cities(id) ON DELETE CASCADE,
            UNIQUE (user_id, city_id)
        )
        """
    )

    # Brute-force throttle for logins (DB-backed so it survives serverless
    # instances). Keyed by username or source IP.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS login_throttle (
            id           TEXT PRIMARY KEY,
            fails        INTEGER NOT NULL DEFAULT 0,
            first_fail   DOUBLE PRECISION,
            locked_until DOUBLE PRECISION
        )
        """
    )

    # Login audit: successful and failed sign-ins, shown in the Activity Log.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS login_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER,
            username   TEXT NOT NULL DEFAULT '',
            full_name  TEXT NOT NULL DEFAULT '',
            role       TEXT NOT NULL DEFAULT '',
            event      TEXT NOT NULL DEFAULT 'login',
            ip         TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )
