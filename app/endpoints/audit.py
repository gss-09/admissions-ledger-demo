"""Activity Log endpoints (admin only): the unified per-category log and the
single-record cleanup."""

from app.data import audit


class AuditApi:
    def activity_log(self, limit=400):
        if not self._is_admin():
            return {"login": [], "edit": []}
        return audit.activity_log(int(limit))

    def log_delete(self, src, ref):
        if not self._is_admin():
            return {"ok": False, "message": "Admins only."}
        if src == "edit":
            audit.delete_edit(ref)
        elif src == "login":
            audit.delete_login_record(ref)
        else:
            return {"ok": False, "message": "Unknown record."}
        return {"ok": True}
