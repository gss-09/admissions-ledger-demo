"""
Schema creation and first-run seeding.

``init_db()`` runs at every boot but is cheap on an already-current database: a
single ``schema_version`` probe short-circuits the whole thing, so a serverless
cold start costs ONE round-trip instead of many. The full build runs only on a
brand-new database or after ``SCHEMA_VERSION`` is bumped — it creates tables IF
NOT EXISTS (``tables.py``), seeds the built-in roles, and (brand-new database
only) creates a single admin account with a RANDOM password printed once to the
server log (``seeds.py``).

IMPORTANT: bump ``SCHEMA_VERSION`` whenever you add or change anything in this
package (a table, column or role seed); otherwise warm databases skip the new
step. The full build is idempotent, so re-running it is always safe.
"""

from app import db
from app.schema.seeds import seed_admin, seed_builtin_roles, seed_org
from app.schema.tables import create_tables

# Bumped whenever the schema/seed changes. Stored in `settings` as
# `schema_version`; a matching value lets init_db() return after one query.
SCHEMA_VERSION = 12


def _schema_is_current(conn):
    """True when the database already reports the current SCHEMA_VERSION. Any
    error — most often a brand-new database with no ``settings`` table yet —
    means 'not current', so the full idempotent build runs."""
    try:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = 'schema_version'").fetchone()
    except Exception:
        return False
    return bool(row) and row["value"] == str(SCHEMA_VERSION)


def init_db():
    """Create tables and seed defaults. Safe to call on every launch; returns
    after a single probe when the database is already at SCHEMA_VERSION."""
    probe = db.connect()
    try:
        if _schema_is_current(probe):
            return
    finally:
        probe.close()

    conn = db.connect()

    create_tables(conn)
    seed_builtin_roles(conn)
    seed_org(conn)
    conn.commit()

    # First-run only: create one admin with a RANDOM password (never a known
    # default). Printed once so the operator can sign in and change it.
    if conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"] == 0:
        seed_admin(conn)

    # Record the version LAST, so a half-finished build is never marked current.
    db.set_setting("schema_version", SCHEMA_VERSION, conn)

    conn.close()
