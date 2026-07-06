"""
Shared foundation for the per-domain Api mixins: the instance state set up by
the dispatcher (``user`` / ``_ip`` / ``_detail``) and the private helpers used
by more than one domain. Underscore-prefixed names are never reachable as
endpoints (the dispatcher rejects them by name).
"""

from app import permissions
from app.data import roles as roles_db, users as users_db


def _public_user(row):
    """The safe subset of a user row sent to the client / stored in the cookie.
    City bindings (`city_ids`/`city_names`) ride along when the row carries them
    (e.g. from ``users_db.list_users``) so the Users screen can render them; the
    cookie/login row omits them — server gating always re-reads the DB."""
    if not row:
        return None
    out = {"id": row["id"], "username": row["username"],
           "full_name": row["full_name"], "role": row["role"],
           "role_label": roles_db.role_label(row["role"])}
    if "city_ids" in row:
        out["city_ids"] = row["city_ids"]
        out["city_names"] = row.get("city_names", [])
        out["all_cities"] = permissions.user_is_org_wide(
            row["role"], row["city_ids"])
    return out


class ApiBase:
    def __init__(self):
        self.user = None
        self.window = None
        self._detail = ""   # human label of what an edit touched (for the audit log)
        self._scope_cached = False
        self._scope = None   # per-request cache of _campus_scope()

    def _note(self, text):
        self._detail = (text or "")

    def _who(self):
        if not self.user:
            return "Unknown"
        return f"{self.user['full_name']} (@{self.user['username']})"

    def _is_admin(self):
        return bool(self.user) and self.user.get("role") == "admin"

    def _can_view(self, module):
        # Module-view gate for content reads: the dispatcher only registry-checks
        # writes (EDIT_ACTIONS) and role-metadata reads (VIEW_READS), so without
        # this a role could fetch data behind a screen its menu doesn't include.
        return bool(self.user) and permissions.role_can_view(self.user["role"], module)

    def _can_view_student_data(self):
        # The student payload feeds Students AND every analytics screen (AGMs,
        # Execs, Averages, Income, Expenditure). So the read is authorised when the
        # role can view ANY of those modules — gating the data, not each screen.
        if self._is_admin():
            return True
        return bool(self.user) and any(
            permissions.role_can_view(self.user["role"], m)
            for m in permissions.STUDENT_DATA_MODULES)

    # ---------------------------------------------------------------- field tiers
    # The shared student payload is projected per tab. These decide which sensitive
    # columns the caller receives; the endpoints strip the rest after the read.

    def _can_view_contact(self):
        # Phones / father / appn no — the directory's record fields. Only the
        # Students screen needs them; analytics tabs never show them.
        return self._is_admin() or (
            bool(self.user) and permissions.role_can_view(self.user["role"], "students"))

    def _can_view_money(self):
        # `final_fee` — any money-bearing module (students/income/averages/expenditure).
        if self._is_admin():
            return True
        return bool(self.user) and any(
            permissions.role_can_view(self.user["role"], m)
            for m in permissions.MONEY_MODULES)

    def _can_view_cost(self):
        # Exec `total_amount` (recruiter MONEY/disbursement) — Expenditure only.
        return self._is_admin() or (
            bool(self.user) and permissions.role_can_view(self.user["role"], "expenditure"))

    def _can_view_target(self):
        # Exec/AGM admission `target` (a goal, not money) — the tabs that SHOW the
        # Target column: AGMs, Execs, Expenditure. Not students/income/averages.
        if self._is_admin():
            return True
        return bool(self.user) and any(
            permissions.role_can_view(self.user["role"], m)
            for m in permissions.TARGET_MODULES)

    # ------------------------------------------------------------- campus scoping
    def _campus_scope(self):
        """The caller's campus scope, read DB-fresh every request (never the cookie),
        so an admin's binding change takes effect on the user's next call. Returns
        ``None`` when org-wide (admin or no CITY bindings) else a list of campus
        NAMES — the campuses of the user's bound cities, expanded live (so a campus
        added to a bound city auto-includes). The org-wide test keys on the user's
        CITY ids, not the expanded campus list, so a bound-but-empty city scopes to
        nothing rather than falling back to org-wide. Cached per request."""
        if not self._scope_cached:
            role = (self.user or {}).get("role")
            city_ids = [] if not self.user else users_db.user_city_ids(self.user["id"])
            if permissions.user_is_org_wide(role, city_ids):
                self._scope = None
            else:
                self._scope = users_db.user_campus_names(self.user["id"])
            self._scope_cached = True
        return self._scope

    def _campus_in_scope(self, name):
        """True when `name` is within the caller's scope (org-wide ⇒ always True)."""
        scope = self._campus_scope()
        return scope is None or (name in scope)

    def _campus_set_in_scope(self, names):
        """True when EVERY campus in `names` is within the caller's scope (org-wide ⇒
        always True). An org item touching any out-of-scope campus is off-limits."""
        scope = self._campus_scope()
        if scope is None:
            return True
        allowed = set(scope)
        return all(n in allowed for n in (names or []))
