"""Roles & Permissions endpoints: the assignable-role list, the module matrix,
the caller's own perms, and the admin role editor."""

from app import permissions
from app.config import MODULES, EDITABLE_MODULES
from app.data import roles as roles_db, users as users_db

# A role that can EDIT `users` (manage accounts) may only be held by org-wide users
# (access to ALL campuses) — see UsersApi._block_scoped_user_admin. Enforced here too
# so the Roles screen can't grant Users-edit to a role a city-bound user already holds.
_SCOPED_ADMIN_ROLE = ("Can't grant Users access to this role — {names} "
                      "{verb} city-bound. An account that can manage users must have "
                      "all-campus (org-wide) access; set them to “All cities” first.")


def _bound_holders(key):
    """Usernames of city-bound users holding role `key` (empty ⇒ all org-wide)."""
    return ["@" + u["username"] for u in users_db.list_users()
            if u["role"] == key and users_db.user_city_ids(u["id"])]


class RolesApi:
    def roles(self):
        # Assignable roles ("admin" excluded). Fetched at boot by every user.
        return [{"key": r["key"], "label": r["label"]}
                for r in roles_db.list_roles() if r["key"] != "admin"]

    def roles_manage_list(self):
        return roles_db.list_roles()

    def role_modules(self):
        return [{"key": k, "label": MODULES[k]["label"], "icon": MODULES[k]["icon"],
                 "editable": k in EDITABLE_MODULES}
                for k in MODULES if k != "home"]

    def my_perms(self):
        role = self.user["role"] if self.user else None
        if role == "admin":
            return {k: "edit" for k in MODULES}
        return permissions.role_perms(role) if role else {}

    def role_create(self, label, menu=None, editable=None):
        ok, message, key = roles_db.create_role(label, menu or [], editable or [])
        if ok:
            self._note(label)
        return {"ok": ok, "message": message, "key": key}

    def role_update(self, key, label, menu=None, editable=None):
        if "users" in (editable or []):
            bound = _bound_holders(key)
            if bound:
                return {"ok": False, "message": _SCOPED_ADMIN_ROLE.format(
                    names=", ".join(bound),
                    verb="are" if len(bound) > 1 else "is")}
        ok, message = roles_db.update_role(key, label, menu or [], editable or [])
        if ok:
            self._note(label or roles_db.role_label(key))
        return {"ok": ok, "message": message}

    def role_delete(self, key):
        label = roles_db.role_label(key)
        ok, message = roles_db.delete_role(key)
        if ok:
            self._note(label)
        return {"ok": ok, "message": message}
