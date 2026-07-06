"""User Management endpoints — admin, or a role granted EDIT on the `users`
module (delegated account management). Delegates have NO admin power: they can't
create/grant the admin role, nor touch an existing admin account. Self-guards keep
anyone from deleting/demoting their own account or removing the last administrator."""

from app import permissions, security
from app.data import users as users_db, audit

from app.endpoints._base import _public_user

_ADMIN_ONLY = "Only an administrator can manage administrator accounts."
_SCOPED_ADMIN = ("An account that can manage users must have all-campus "
                 "(org-wide) access. Set Cities to “All cities”, or pick a "
                 "role without Users access.")


class UsersApi:
    def _manages_users(self):
        """May the caller manage accounts at all? Admin, or a non-admin role with
        EDIT on `users`. (The dispatcher already enforces EDIT on the write
        endpoints via EDIT_ACTIONS; repeated here so the read `users_list` shares
        the exact same gate.)"""
        return self._is_admin() or (
            bool(self.user)
            and permissions.role_can_edit(self.user["role"], "users"))

    def _block_scoped_user_admin(self, role, city_ids):
        """HARD BLOCK (even for an admin): a role that can EDIT `users` — i.e. manage
        accounts — may only be held by an org-wide user (access to ALL campuses). So
        refuse to create/keep a city-bound account with user-management power.
        `city_ids` is the account's EFFECTIVE city binding (empty/None ⇒ org-wide;
        admin is always org-wide). Returns a denial dict, or None when allowed."""
        if role == "admin":
            return None
        if city_ids and permissions.role_can_edit(role, "users"):
            return {"ok": False, "message": _SCOPED_ADMIN}
        return None

    def users_list(self):
        if not self._manages_users():
            return []
        return [_public_user(u) for u in users_db.list_users()]

    def users_create(self, full_name, username, role, password, city_ids=None):
        if not self._manages_users():
            return {"ok": False, "message": "You don't have permission to manage accounts."}
        if role == "admin" and not self._is_admin():
            return {"ok": False, "message": _ADMIN_ONLY}
        denied = self._block_scoped_user_admin(role, city_ids)
        if denied:
            return denied
        full_name = (full_name or "").strip()
        username = (username or "").strip()
        if not (full_name and username and password):
            return {"ok": False, "message": "All fields are required."}
        if security.password_too_short(password):
            return {"ok": False, "message": "Password must be at least 8 characters."}
        ok, message, uid = users_db.create_user(username, full_name, role, password)
        if ok:
            # city_ids None/[] ⇒ no rows ⇒ org-wide (the empty-set = all rule).
            users_db.set_user_cities(uid, city_ids or [])
            self._note(f"{full_name} (@{username})")
        return {"ok": ok, "message": message}

    def users_update(self, user_id, full_name, username, role, password=None,
                     city_ids=None):
        if not self._manages_users():
            return {"ok": False, "message": "You don't have permission to manage accounts."}
        full_name = (full_name or "").strip()
        username = (username or "").strip()
        if not (full_name and username):
            return {"ok": False, "message": "Name and username are required."}
        if password and security.password_too_short(password):
            return {"ok": False, "message": "Password must be at least 8 characters."}
        uid = int(user_id)
        target = users_db.get_user(uid)
        if not target:
            return {"ok": False, "message": "User not found."}
        is_self = bool(self.user and uid == self.user["id"])
        if is_self:
            role = self.user["role"]   # can't change your own role
        # Delegates (non-admins) can neither edit an existing admin nor grant admin.
        if not self._is_admin() and (target.get("role") == "admin" or role == "admin"):
            return {"ok": False, "message": _ADMIN_ONLY}
        # Never demote the last remaining administrator.
        if target.get("role") == "admin" and role != "admin" and users_db.admin_count() <= 1:
            return {"ok": False, "message": "You can't change the last administrator's role."}
        # Hard block: a user-managing role must stay org-wide. Check the EFFECTIVE
        # binding — the incoming city_ids, or the current one when left unchanged.
        eff_cities = city_ids if city_ids is not None else users_db.user_city_ids(uid)
        denied = self._block_scoped_user_admin(role, eff_cities)
        if denied:
            return denied
        ok, message = users_db.update_user(uid, full_name, username, role)
        # city_ids is None ⇒ leave bindings untouched (the role-pill quick change
        # and self-edits send no cities); a list (incl. []) ⇒ replace-set.
        if ok and city_ids is not None:
            users_db.set_user_cities(uid, city_ids)
        if ok and password:
            users_db.set_password(uid, password)
            audit.log_password_change(users_db.get_user(uid), self.user, kind="account_edit")
        if ok and is_self:
            self.user["full_name"] = full_name
            self.user["username"] = username
        if ok:
            self._note(f"{full_name} (@{username})")
        return {"ok": ok, "message": message}

    def users_delete(self, user_id):
        if not self._manages_users():
            return {"ok": False, "message": "You don't have permission to manage accounts."}
        uid = int(user_id)
        if self.user and uid == self.user["id"]:
            return {"ok": False, "message": "You can't delete your own account."}
        u = users_db.get_user(uid)
        # Delegates (non-admins) can't delete an administrator account.
        if u and u.get("role") == "admin" and not self._is_admin():
            return {"ok": False, "message": _ADMIN_ONLY}
        if u and u.get("role") == "admin" and users_db.admin_count() <= 1:
            return {"ok": False, "message": "You can't delete the last administrator."}
        users_db.delete_user(uid)
        if u:
            self._note(f"{u['full_name']} (@{u['username']})")
        return {"ok": True, "message": "Account deleted."}
