"""Admissions endpoints: the full ledger read (+ dropdown metadata), add /
update / delete, and the CSV bulk import. Writes are gated to editor/admin by
``config.EDIT_ACTIONS``; the import is admin-only (see config)."""

from app.config import STATUSES
from app.data import students as students_db


# Sensitive columns stripped from the payload when the caller lacks the tab that
# legitimately shows them (campus rows are filtered separately, in the data layer).
_CONTACT_COLS = ("appn_no", "father_name", "mobile1", "mobile2")
_MONEY_COLS = ("final_fee",)


class StudentsApi:
    def students(self):
        """All students + the distinct dropdown values, in one payload (mirrors
        the original /api/data). Readable by any role that can view a student-data
        screen (Students or any analytics tab) — gating the data, not each screen.

        Scoped on two axes the caller may not cross: campus ROWS (bound users see
        only their campuses) and sensitive FIELDS (contact PII needs the Students
        tab; `final_fee` needs a money tab). Both enforced here, server-side."""
        if not self._can_view_student_data():
            return {"students": [], "meta": {"statuses": STATUSES}}
        scope = self._campus_scope()
        meta = students_db.distinct_meta(scope)
        meta["statuses"] = STATUSES
        rows = students_db.list_all(scope)
        drop = []
        if not self._can_view_contact():
            drop += _CONTACT_COLS
        if not self._can_view_money():
            drop += _MONEY_COLS
        if drop:
            for r in rows:
                for col in drop:
                    r.pop(col, None)
        return {"students": rows, "meta": meta}

    def student_add(self, data):
        data = data or {}
        if not self._campus_in_scope((data.get("campus") or "").strip()):
            return {"ok": False,
                    "message": "You can only add admissions for your campus(es)."}
        ok, message, sid = students_db.create_student(data, self._who())
        if ok:
            self._note(data.get("student_name", ""))
        return {"ok": ok, "message": message, "id": sid}

    def student_update(self, student_id, data):
        data = data or {}
        student = students_db.get_student(student_id)
        # A bound user may neither edit an out-of-scope record nor move a record out
        # of (or into) scope: BOTH the existing campus and the target campus must be
        # in scope. (IDOR-safe — the gate doesn't trust the row id alone.)
        if student is not None:
            if not self._campus_in_scope((student.get("campus") or "").strip()) or \
               not self._campus_in_scope((data.get("campus") or "").strip()):
                return {"ok": False,
                        "message": "You can only edit admissions for your campus(es)."}
        ok, message = students_db.update_student(student_id, data)
        if ok and student:
            self._note(data.get("student_name") or student.get("student_name", ""))
        return {"ok": ok, "message": message}

    def student_delete(self, student_id):
        # Deleting is admin-only; editors can add/update but not remove records.
        if not self._is_admin():
            return {"ok": False, "message": "Only an administrator can delete admissions."}
        student = students_db.get_student(student_id)
        ok, message = students_db.delete_student(student_id)
        if ok and student:
            self._note(student.get("student_name", ""))
        return {"ok": ok, "message": message}

    def students_import(self, rows):
        # Bulk import is admin-only; editors add students one at a time.
        if not self._is_admin():
            return {"ok": False, "message": "Only an administrator can bulk-import."}
        if not isinstance(rows, list):
            return {"ok": False, "message": "Expected a list of rows."}
        res = students_db.merge_rows(rows, self._who())
        self._note(f"{res['added']} added, {res['updated']} updated, {res['skipped']} skipped")
        return {"ok": True, **res}
