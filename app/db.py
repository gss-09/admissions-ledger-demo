"""
Database access layer: the connection pool and small SQL helpers.

The app runs against a hosted Postgres (Supabase) configured via DATABASE_URL.
The pool is created lazily on first use, so this module can be imported (for
tests/tooling) without a database — DATABASE_URL is only required once a query
actually runs.

Every query in the data layer uses ``?`` placeholders and parameter tuples.
``_Conn`` rewrites ``?`` → ``%s`` for psycopg. There is no string interpolation
of user input anywhere; the only dynamic SQL is whitelisted column names.
"""

import os
from datetime import datetime, timedelta, timezone

import psycopg
from psycopg.rows import dict_row
from psycopg import errors as _pg_errors
from psycopg_pool import ConnectionPool

# Raised on a UNIQUE / duplicate-key violation.
INTEGRITY_ERRORS = (psycopg.IntegrityError, _pg_errors.UniqueViolation)

_POOL = None


def _database_url():
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Admissions Ledger uses a hosted Postgres "
            "database; set DATABASE_URL to the Supabase connection string before "
            "starting."
        )
    return url


def _pool():
    """The shared connection pool, created on first use."""
    global _POOL
    if _POOL is None:
        # prepare_threshold=None is required for Supabase's transaction pooler
        # (port 6543). autocommit keeps read queries from leaving an open
        # transaction; write helpers still call commit() explicitly.
        _POOL = ConnectionPool(
            _database_url(),
            min_size=1,
            max_size=8,
            kwargs={"row_factory": dict_row, "prepare_threshold": None,
                    "autocommit": True},
            open=True,
        )
    return _POOL


class _Conn:
    """Thin wrapper over a pooled connection that accepts ``?`` placeholders and
    the SQLite-flavoured ``INTEGER PRIMARY KEY AUTOINCREMENT`` used in the
    schema, returning dict rows."""

    def __init__(self, raw):
        self.raw = raw

    def _adapt(self, sql):
        sql = sql.replace("?", "%s")
        sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
        return sql

    def execute(self, sql, params=()):
        cur = self.raw.cursor()
        cur.execute(self._adapt(sql), params)
        return cur

    def commit(self):
        self.raw.commit()

    def rollback(self):
        self.raw.rollback()

    def close(self):
        _pool().putconn(self.raw)   # return to the pool (it resets state)

    # Context-manager support guarantees the connection is returned to the pool
    # even if the body raises (otherwise a handful of errors exhaust the pool and
    # hang the app). On error we roll back first, then always putconn.
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type is not None:
                try:
                    self.raw.rollback()
                except Exception:
                    pass
        finally:
            self.close()
        return False


def connect():
    return _Conn(_pool().getconn())


def insert(conn, sql, params):
    """Run an INSERT and return the new row's id."""
    return conn.execute(sql + " RETURNING id", params).fetchone()["id"]


def columns(conn, table):
    """Column names of a table (used by the schema migrations)."""
    return [r["column_name"] for r in conn.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = ?", (table,)).fetchall()]


# India Standard Time. India observes no daylight saving, so a fixed +5:30 offset
# is exact year-round — and doesn't depend on the tz database being present in the
# serverless runtime. Vercel's functions run in UTC, so we set this explicitly.
IST = timezone(timedelta(hours=5, minutes=30))


def now_dt():
    """Current moment as an IST-aware datetime (for date math)."""
    return datetime.now(IST)


def now():
    """Current IST timestamp as 'YYYY-MM-DD HH:MM' — the string every row stores."""
    return now_dt().strftime("%Y-%m-%d %H:%M")


# --------------------------------------------------------------------------
# Settings key/value store
# --------------------------------------------------------------------------

def get_setting(key, default=None):
    with connect() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default


def set_setting(key, value, conn=None):
    # When called with a caller-owned conn, don't wrap it (the caller closes it);
    # otherwise open our own and release it via the context manager.
    if conn is not None:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
        )
        conn.commit()
        return
    with connect() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
        )
        conn.commit()
