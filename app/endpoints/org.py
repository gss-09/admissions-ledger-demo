"""
Recruiting-org endpoints: the cities / campuses / courses / AGM / exec management
screen.

The dispatcher's EDIT gate already requires *edit on the ``org`` module* for every
write below (they're in ``config.EDIT_ACTIONS``), so the whole Manage-Org screen —
including campuses, cities and courses — is governed by one role permission
(campuses are no longer hard admin-only; an admin can grant org-edit to a role).
"""

from app.data import org as org_db

# Denials shared by the org write guards.
_NOT_ORG_WIDE = {"ok": False, "message":
                 "Only an organisation-wide user can change the org structure "
                 "(cities and campuses)."}
_OUT_OF_SCOPE = {"ok": False, "message": "That's outside your campus scope."}


class OrgApi:
    # ---------------------------------------------------------- write guards
    # Bound (campus-scoped) users may manage only the AGMs / execs / courses under
    # their campuses; the org STRUCTURE (cities + campus create/rename/delete/move)
    # stays org-wide-only. Org-wide callers (admin / no bindings) bypass both.

    def _deny_unless_org_wide(self):
        return None if self._campus_scope() is None else _NOT_ORG_WIDE

    def _deny_unless_campuses(self, campus_names):
        return None if self._campus_set_in_scope(campus_names) else _OUT_OF_SCOPE

    def org_data(self):
        """Cities + campuses (with courses) + AGMs (with campuses + execs). Needs
        VIEW on ``org``; a bound user sees only their campuses' slice of the tree."""
        if not self._can_view("org"):
            return {"cities": [], "campuses": [], "agms": []}
        return org_db.org_tree(self._campus_scope())

    def exec_expenditure(self):
        """AGM teams + per-exec total_amount/target, for the Expenditure screen (and
        the Target column on the AGMs/Execs tabs). Rides on the student-data view
        group (same access as Averages/AGMs/Execs/Income), so the roster NAMES reach
        the Execs screen for any student-data viewer. The two sensitive figures are
        each field-tiered to the tabs that show them: the MONEY figures `total_amount`
        and its four breakdown pieces (`salary`/`gen_exp`/`incentive`/`gift`) plus the
        per-team `rent` (on the AGM) → Expenditure only (`_can_view_cost`); the
        admission `target` (a goal, not
        money) → the tabs with a Target column, i.e. AGMs/Execs/Expenditure
        (`_can_view_target`). An income/averages-only viewer gets neither."""
        if not self._can_view_student_data():
            return {"agms": []}
        tree = org_db.expenditure_tree(self._campus_scope())
        strip_cost = not self._can_view_cost()
        strip_target = not self._can_view_target()
        if strip_cost or strip_target:
            for agm in tree:
                if strip_cost:
                    agm.pop("rent", None)   # team rent is a cost figure
                for e in agm["execs"]:
                    if strip_cost:
                        for f in ("total_amount", "salary", "gen_exp",
                                  "incentive", "gift"):
                            e.pop(f, None)
                    if strip_target:
                        e.pop("target", None)
        return {"agms": tree}

    # -------------------------------------------------- cities (org-wide only)
    def city_create(self, name):
        denied = self._deny_unless_org_wide()
        if denied:
            return denied
        ok, message, cid = org_db.create_city(name)
        if ok:
            self._note(name)
        return {"ok": ok, "message": message, "id": cid}

    def city_rename(self, city_id, name):
        denied = self._deny_unless_org_wide()
        if denied:
            return denied
        ok, message = org_db.rename_city(city_id, name)
        if ok:
            self._note(name)
        return {"ok": ok, "message": message}

    def city_delete(self, city_id):
        denied = self._deny_unless_org_wide()
        if denied:
            return denied
        ok, message = org_db.delete_city(city_id)
        return {"ok": ok, "message": message}

    # -------------------------------------------------- campuses (org-wide only)
    def campus_create(self, name, city_id=None):
        denied = self._deny_unless_org_wide()
        if denied:
            return denied
        ok, message, cid = org_db.create_campus(name, city_id)
        if ok:
            self._note(name)
        return {"ok": ok, "message": message, "id": cid}

    def campus_rename(self, campus_id, name):
        denied = self._deny_unless_org_wide()
        if denied:
            return denied
        ok, message = org_db.rename_campus(campus_id, name)
        if ok:
            self._note(name)
        return {"ok": ok, "message": message}

    def campus_delete(self, campus_id):
        denied = self._deny_unless_org_wide()
        if denied:
            return denied
        ok, message = org_db.delete_campus(campus_id)
        return {"ok": ok, "message": message}

    def campus_set_city(self, campus_id, city_id=None):
        denied = self._deny_unless_org_wide()
        if denied:
            return denied
        ok, message = org_db.set_campus_city(campus_id, city_id)
        return {"ok": ok, "message": message}

    # -------------------------------------------------- courses (campus-scoped)
    def course_create(self, campus_id, name):
        denied = self._deny_unless_campuses([org_db.campus_name_by_id(campus_id)])
        if denied:
            return denied
        ok, message, cid = org_db.create_course(campus_id, name)
        if ok:
            self._note(name)
        return {"ok": ok, "message": message, "id": cid}

    def course_rename(self, course_id, name):
        denied = self._deny_unless_campuses([org_db.course_campus_name(course_id)])
        if denied:
            return denied
        ok, message = org_db.rename_course(course_id, name)
        if ok:
            self._note(name)
        return {"ok": ok, "message": message}

    def course_delete(self, course_id):
        denied = self._deny_unless_campuses([org_db.course_campus_name(course_id)])
        if denied:
            return denied
        ok, message = org_db.delete_course(course_id)
        return {"ok": ok, "message": message}

    # -------------------------------------------------- AGMs (city-bound, scoped)
    def agm_create(self, name, city_id=None):
        denied = self._deny_unless_campuses(org_db.city_campus_names(city_id))
        if denied:
            return denied
        ok, message, aid = org_db.create_agm(name, city_id)
        if ok:
            self._note(name)
        return {"ok": ok, "message": message, "id": aid}

    def agm_set_city(self, agm_id, city_id=None):
        # A bound user may only touch an AGM wholly within their scope (its current
        # city's campuses) and may only move it to a city within their scope.
        existing = org_db.agm_campus_names(agm_id)
        new = org_db.city_campus_names(city_id)
        denied = self._deny_unless_campuses(existing + new)
        if denied:
            return denied
        ok, message = org_db.set_agm_city(agm_id, city_id)
        return {"ok": ok, "message": message}

    def agm_rename(self, agm_id, name):
        denied = self._deny_unless_campuses(org_db.agm_campus_names(agm_id))
        if denied:
            return denied
        ok, message = org_db.rename_agm(agm_id, name)
        if ok:
            self._note(name)
        return {"ok": ok, "message": message}

    def agm_delete(self, agm_id):
        denied = self._deny_unless_campuses(org_db.agm_campus_names(agm_id))
        if denied:
            return denied
        ok, message = org_db.delete_agm(agm_id)
        return {"ok": ok, "message": message}

    # -------------------------------------------------- execs (campus-scoped)
    def exec_create(self, agm_id, name):
        denied = self._deny_unless_campuses(org_db.agm_campus_names(agm_id))
        if denied:
            return denied
        ok, message, eid = org_db.create_exec(agm_id, name)
        if ok:
            self._note(name)
        return {"ok": ok, "message": message, "id": eid}

    def exec_rename(self, exec_id, name):
        denied = self._deny_unless_campuses(org_db.exec_campus_names(exec_id))
        if denied:
            return denied
        ok, message = org_db.rename_exec(exec_id, name)
        if ok:
            self._note(name)
        return {"ok": ok, "message": message}

    def exec_delete(self, exec_id):
        denied = self._deny_unless_campuses(org_db.exec_campus_names(exec_id))
        if denied:
            return denied
        ok, message = org_db.delete_exec(exec_id)
        return {"ok": ok, "message": message}
