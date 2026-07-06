"""
Authorization: every access decision in the app is made here.

Two layers:

1. Role capability helpers — can a role view/edit a module, manage another user.
   Built on the raw readers in ``app.data.roles``.

2. The endpoint access registry + ``deny_reason`` — the single, auditable gate
   the dispatcher applies to *every* request before an endpoint runs:
     * PUBLIC          — callable without a session.
     * EDIT_ACTIONS    — needs EDIT on the owning module (writes).
     * VIEW_READS      — reads that expose role/permission metadata; need VIEW on
                         the owning module (or admin).
     * everything else — needs a valid session.

Two data-scoping axes layer on top of the module gate (both enforced server-side,
at the two student-data egress endpoints):

  * CITY rows — a user is bound to a set of cities (``user_cities``) and sees only
    those cities' campuses (expanded live); an empty set ⇒ org-wide, and admin is
    always org-wide. See ``user_is_org_wide`` + ``ApiBase._campus_scope``.
  * SENSITIVE fields — the shared student payload is projected per tab: contact PII
    (phones / father / appn no) only for ``students`` viewers, money (``final_fee``)
    only for a money module, exec cost only for ``expenditure``. See the
    ``_can_view_contact`` / ``_can_view_money`` / ``_can_view_cost`` helpers on
    ``ApiBase``.
"""

from app.config import EDIT_ACTIONS
from app.data import roles as roles_data

# Screens that all render from the student payload. A role that can view ANY of
# these may load the shared student reads (api().students() / exec_expenditure());
# the per-module toggles only decide which screens show. See
# ApiBase._can_view_student_data.
STUDENT_DATA_MODULES = ("students", "agms", "execs", "averages", "income", "expenditure")

# Modules whose purpose is money/fees: viewing any of them earns the `final_fee`
# field in the student payload (the directory `students` is included so editors can
# still see/edit a student's fee). The Home "Reported income" hero is gated more
# tightly, on the `income` tab specifically (a UI check). See ApiBase._can_view_money.
MONEY_MODULES = ("students", "income", "averages", "expenditure")

# Modules that SHOW the admission `target` (a goal, not money) from exec_expenditure():
# the AGMs and Execs tabs (Target column) and the Expenditure tab. Viewing any of them
# earns the `target` field; income/averages/students-only viewers don't. The roster
# names still reach any student-data viewer (tier-3); only `target`/`total_amount` are
# field-tiered. See ApiBase._can_view_target.
TARGET_MODULES = ("agms", "execs", "expenditure")


# --------------------------------------------------------------------------
# Role capability helpers
# --------------------------------------------------------------------------

def role_can_view(role, module):
    if role == "admin":
        return True
    return module in roles_data.role_menu(role)


def role_can_edit(role, module):
    """Whether a role may CHANGE (not just view) a module. Admin: always."""
    if role == "admin":
        return True
    return module in roles_data.role_editable(role)


def role_perms(role):
    """Map of module → 'edit' | 'view' for a role."""
    if role == "admin":
        return {"_all": "edit"}
    menu = roles_data.role_menu(role)
    editable = set(roles_data.role_editable(role))
    return {m: ("edit" if m in editable else "view") for m in menu}


def user_is_org_wide(role, bindings):
    """Whether a user sees the whole org: admin always, otherwise only when they have
    NO bindings (empty set ⇒ all). `bindings` is the user's CITY list (ids or names);
    pure — the caller passes it (I/O-free, like the rest of this module)."""
    return role == "admin" or not bindings


def can_manage(actor, target):
    """Who may manage (edit/delete) whom. Only an admin manages accounts, and
    never their own (self-guards live in the endpoints). A custom role can never
    outrank admin."""
    if not actor or not target or actor["id"] == target["id"]:
        return False
    return actor.get("role") == "admin"


# --------------------------------------------------------------------------
# Endpoint access registry
# --------------------------------------------------------------------------

# Callable without a session. ``bootstrap`` is public because boot() calls it
# before login to probe the session cookie; it returns {"user": None} when
# signed out and only bundles per-user reads once a valid session exists.
PUBLIC = {"login", "logout", "session", "bootstrap"}

# Never callable from the web (internal attributes / dunder-ish names).
DISALLOWED = {"window", "user"}

# Reads that expose role/permission metadata. Allowed only for admin or a role
# that can VIEW the owning module (the screen that legitimately uses the data).
VIEW_READS = {
    "roles_manage_list": ("roles",),
    "role_modules":      ("roles",),
}

_VIEW_ONLY_MSG = "You have view-only access to this section."
_NO_ACCESS_MSG = "You don't have access to this section."


def deny_reason(user, method):
    """Return None when the call is allowed, else a (json_body, status_code)
    tuple describing the denial. Assumes `method` is a real, non-public Api
    method and `user` is the (already-authenticated) session user."""
    role = (user or {}).get("role")

    module = EDIT_ACTIONS.get(method)
    if module:
        if not (role and role_can_edit(role, module)):
            return ({"ok": False, "message": _VIEW_ONLY_MSG}, 200)
        return None

    mods = VIEW_READS.get(method)
    if mods:
        if not (role == "admin" or any(role_can_view(role, m) for m in mods)):
            return ({"ok": False, "message": _NO_ACCESS_MSG}, 403)
        return None

    return None
