"""Self-service profile endpoint (admin-only in the public demo), plus the
admin-only password-change log. Self-service password changes were removed on
purpose: every account here is a shared demo account, so letting one visitor
change a password would lock the demo for everyone else. Passwords only change
via reseeding (or an admin reset)."""

from app.data import users as users_db, audit


class AccountApi:
    # ------------------------------------------------- self-service profile
    def update_my_profile(self, full_name, username):
        if not self.user:
            return {"ok": False, "message": "You are not signed in."}
        if self.user.get("role") != "admin":
            return {"ok": False,
                    "message": "Only an administrator can change their name."}
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

    # ----------------------------------------------------- admin password log
    def password_logs(self, limit=200):
        if not self._is_admin():
            return {"ok": False, "message": "Admins only.", "logs": []}
        return {"ok": True, "logs": audit.password_changes(int(limit))}
