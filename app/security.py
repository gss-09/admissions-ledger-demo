"""
Password hashing and brute-force throttling.

Passwords are stored as PBKDF2-SHA256 ('iterations$salt$hash') and verified with
a constant-time compare. Repeated failed logins are rate limited with a small
DB-backed counter so the lock survives across the stateless serverless instances
on Vercel.
"""

import hashlib
import secrets
import time

from app import db

# --- password policy -------------------------------------------------------
MIN_PASSWORD_LEN = 8

# PBKDF2-SHA256 work factor (the OWASP-recommended minimum). New hashes store
# their iteration count ('iterations$salt$hash'); legacy two-part hashes
# ('salt$hash') were created at 100k and verify_password still accepts them —
# they are upgraded in place on the next successful login.
PBKDF2_ITERATIONS = 600_000
_LEGACY_ITERATIONS = 100_000

# --- login throttle policy -------------------------------------------------
MAX_FAILS = 5          # failures allowed within the window before locking
IP_MAX_FAILS = 20      # looser per-IP cap: catches password spraying across
                       # usernames without locking out a shared NAT
WINDOW_SECONDS = 15 * 60
LOCKOUT_SECONDS = 15 * 60


# --------------------------------------------------------------------------
# Password hashing
# --------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Return 'iterations$salt$hash' using PBKDF2-SHA256."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", (password or "").encode(),
                                 salt.encode(), PBKDF2_ITERATIONS)
    return f"{PBKDF2_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    parts = (stored or "").split("$")
    if len(parts) == 3:
        iters_raw, salt, digest = parts
    elif len(parts) == 2:
        iters_raw, (salt, digest) = str(_LEGACY_ITERATIONS), parts
    else:
        return False
    try:
        iterations = int(iters_raw)
    except ValueError:
        return False
    check = hashlib.pbkdf2_hmac("sha256", (password or "").encode(),
                                salt.encode(), iterations)
    return secrets.compare_digest(check.hex(), digest)


def password_needs_rehash(stored: str) -> bool:
    """True when a stored hash predates the current format/work factor."""
    return not (stored or "").startswith(f"{PBKDF2_ITERATIONS}$")


def password_too_short(password: str) -> bool:
    return not password or len(password) < MIN_PASSWORD_LEN


# --------------------------------------------------------------------------
# Login throttle (DB-backed, keyed by a caller-supplied string)
# --------------------------------------------------------------------------

def _key(raw: str) -> str:
    return (raw or "").strip().lower()[:200]


def throttle_status(raw_key: str):
    """Return (locked: bool, seconds_left: int) for a throttle key."""
    key = _key(raw_key)
    if not key:
        return (False, 0)
    with db.connect() as conn:
        row = conn.execute("SELECT locked_until FROM login_throttle WHERE id = ?",
                           (key,)).fetchone()
    if row and row["locked_until"]:
        left = float(row["locked_until"]) - time.time()
        if left > 0:
            return (True, int(left) + 1)
    return (False, 0)


def throttle_fail(raw_key: str, max_fails: int = MAX_FAILS):
    """Record one failed attempt; lock the key once max_fails is reached within
    the rolling window."""
    key = _key(raw_key)
    if not key:
        return
    now = time.time()
    with db.connect() as conn:
        row = conn.execute(
            "SELECT fails, first_fail FROM login_throttle WHERE id = ?", (key,)).fetchone()
        if not row or not row["first_fail"] or (now - float(row["first_fail"]) > WINDOW_SECONDS):
            fails, first_fail = 1, now
        else:
            fails, first_fail = int(row["fails"]) + 1, float(row["first_fail"])
        locked_until = now + LOCKOUT_SECONDS if fails >= max_fails else None
        conn.execute(
            "INSERT INTO login_throttle (id, fails, first_fail, locked_until) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET fails = excluded.fails, "
            "first_fail = excluded.first_fail, locked_until = excluded.locked_until",
            (key, fails, first_fail, locked_until))
        conn.commit()


def throttle_clear(raw_key: str):
    """Clear a key's failure record (called on a successful login)."""
    key = _key(raw_key)
    if not key:
        return
    with db.connect() as conn:
        conn.execute("DELETE FROM login_throttle WHERE id = ?", (key,))
        conn.commit()
