"""Auth/session endpoints (all PUBLIC except ``menu``): login, logout, session,
the one-round-trip bootstrap, and the role-aware menu."""

from app import security
from app.config import MODULES
from app.data import users as users_db, roles as roles_db

from app.endpoints._base import _public_user


class AuthApi:
    def login(self, username, password):
        username = (username or "").strip()
        # Brute-force throttle: lock a username after repeated failures, and the
        # source IP (looser cap) after many failures across ANY usernames. ``_ip``
        # is stamped by the dispatcher — underscore-prefixed, never web-reachable.
        user_key = f"user:{username}"
        ip_key = f"ip:{getattr(self, '_ip', '') or 'unknown'}"
        for key in (user_key, ip_key):
            locked, secs = security.throttle_status(key)
            if locked:
                mins = max(1, secs // 60)
                return {"ok": False, "error":
                        f"Too many failed attempts. Try again in about {mins} minute(s)."}
        row = users_db.authenticate(username, password or "")
        if not row:
            security.throttle_fail(user_key)
            security.throttle_fail(ip_key, max_fails=security.IP_MAX_FAILS)
            return {"ok": False, "error": "Invalid username or password."}
        security.throttle_clear(user_key)
        self.user = _public_user(row)
        return {"ok": True, "user": self.user}

    def logout(self):
        self.user = None
        return {"ok": True}

    def session(self):
        return self.user

    def bootstrap(self):
        """Everything the SPA needs to render its shell, in ONE round trip: the
        current user (or None when signed out) plus the menu/roles/perms that
        boot() would otherwise fetch in three separate calls."""
        if not self.user:
            return {"user": None}
        return {
            "user": self.user,
            "menu": self.menu(),
            "roles": self.roles(),
            "perms": self.my_perms(),
        }

    def menu(self):
        role = self.user["role"] if self.user else "viewer"
        keys = roles_db.role_menu(role)
        return [{"key": k, "label": MODULES[k]["label"], "icon": MODULES[k]["icon"]}
                for k in keys if k in MODULES]
