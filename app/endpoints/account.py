"""Self-service profile/password endpoints, plus the admin-only password-change
log."""

from app import security
from app.data import users as users_db, audit


class AccountApi:
    # ------------------------------------------------- self-service profile
    def update_my_profile(self, full_name, username):
        if not self.user:
            return {"ok": False, "message": "You are not signed in."}
        full_name = (full_name or "").strip()
        username = (username or "").strip()
        if not full_name or not username:
            return {"ok": False, "message": "Name and username are required."}
        ok, message = users_db.update_user(self.user["id"], full_name, username,
                                           self.user["role"])
        if ok:
            self.user["full_name"] = full_name
            self.user["username"] = username
        return {"ok": ok, "message": message, "user": self.user}

    # ------------------------------------------------- self-service password
    def change_my_password(self, current, new):
        if not self.user:
            return {"ok": False, "message": "You are not signed in."}
        if security.password_too_short(new):
            return {"ok": False, "message": "New password must be at least 8 characters."}
        if not users_db.authenticate(self.user["username"], current or ""):
            return {"ok": False, "message": "Your current password is incorrect."}
        users_db.set_password(self.user["id"], new)
        audit.log_password_change(self.user, self.user, kind="self")
        return {"ok": True, "message": "Password changed."}

    # ----------------------------------------------------- admin password log
    def password_logs(self, limit=200):
        if not self._is_admin():
            return {"ok": False, "message": "Admins only.", "logs": []}
        return {"ok": True, "logs": audit.password_changes(int(limit))}
