"""
Static configuration for Admissions Ledger: roles, modules, statuses, labels and
the write-action access map.

These are pure constants (no I/O), shared by the data, permission and endpoint
layers. Runtime configuration that touches the environment lives elsewhere: the
database URL in ``db.py`` and the Flask secret/cookies in ``app/__init__.py``.
"""

# --------------------------------------------------------------------------
# Roles
# --------------------------------------------------------------------------

# Built-in roles seeded on first run. Admins can add custom roles on top, and
# change any role's per-page View/Edit access in the Roles screen.
ROLES = ["admin", "editor", "viewer"]

ROLE_LABELS = {
    "admin": "Administrator",
    "editor": "Editor",
    "viewer": "Viewer",
}

# Default modules (tabs) each built-in role can SEE on first seed. After that an
# admin edits permissions in the Roles screen (stored in the `roles` table).
BUILTIN_ROLE_MENUS = {
    "admin":  "home,students,agms,execs,averages,income,expenditure,org,users,roles,log",
    "editor": "home,students,agms,execs,averages,income,expenditure",
    "viewer": "home,students,agms,execs,averages,income,expenditure",
}

# Per-role edit-rights override at first seed. Default is "editable = the whole
# menu". The editor may edit students; the viewer edits nothing (read-only).
BUILTIN_ROLE_EDITABLE = {
    "editor": "students",
    "viewer": "",
}

# Seniority for who-manages-whom. Unknown (custom) roles are treated as the
# lowest level. Only an admin manages accounts, so this mostly guards against a
# custom role ever outranking admin.
ROLE_RANK = {"admin": 0, "editor": 1, "viewer": 2}


def rank(role):
    return ROLE_RANK.get(role, 9)


# --------------------------------------------------------------------------
# Modules (front-end screens)
# --------------------------------------------------------------------------

# The five analytics screens (agms..expenditure) are VIEW-only modules: they have
# no edit actions, so the Roles screen offers Off/View on them (no Edit). They all
# render from the student payload, so the actual data gate is "can view any
# student-data module" (see permissions.STUDENT_DATA_MODULES) — the toggles just
# decide which screens appear in the sidebar.
MODULES = {
    "home":        {"label": "Home",          "icon": "home"},
    "students":    {"label": "Students",      "icon": "user"},
    "agms":        {"label": "AGMs",          "icon": "network"},
    "execs":       {"label": "Marketing Execs", "icon": "users"},
    "averages":    {"label": "Averages",      "icon": "chart"},
    "income":      {"label": "Income",        "icon": "rupee"},
    "expenditure": {"label": "Expenditure",   "icon": "wallet"},
    "org":         {"label": "Manage Org",    "icon": "building"},
    "users":       {"label": "Users",         "icon": "users"},
    "roles":       {"label": "Roles",         "icon": "shield"},
    "log":         {"label": "Activity Log",  "icon": "history"},
}


# --------------------------------------------------------------------------
# Admission status vocabulary
# --------------------------------------------------------------------------

# The funnel stages a student can be in. Order matters for the status dropdowns.
# (The former "NOT DECIDED" stage was merged into "NOT LIFTING" in SCHEMA_VERSION 2;
# the former "NO STATUS" stage was retired — those students became "YET TO ARRIVE".)
STATUSES = ["REPORTED", "DROPPED", "YET TO ARRIVE", "SETTLED", "NOT LIFTING"]
DEFAULT_STATUS = "YET TO ARRIVE"


# --------------------------------------------------------------------------
# Write actions → module (drives the EDIT permission gate + the audit log)
# --------------------------------------------------------------------------

# Each data-mutating endpoint maps to the module it belongs to. The dispatcher
# blocks the call unless the caller's role has EDIT (not just view) on that
# module (admin bypasses). Anything NOT listed here is treated as read-only.
# Adding a new write endpoint MUST add it here, or it would be allowed for
# view-only roles.
EDIT_ACTIONS = {
    # Admissions (students)
    "student_add": "students", "student_update": "students",
    "student_delete": "students", "students_import": "students",
    # The recruiting org (cities / campuses / courses / AGMs / execs). All governed
    # purely by the `org` edit gate (campuses are no longer hard admin-only).
    "agm_create": "org", "agm_rename": "org", "agm_delete": "org",
    "agm_set_city": "org",
    "exec_create": "org", "exec_rename": "org", "exec_delete": "org",
    "campus_create": "org", "campus_rename": "org", "campus_delete": "org",
    "campus_set_city": "org",
    "city_create": "org", "city_rename": "org", "city_delete": "org",
    "course_create": "org", "course_rename": "org", "course_delete": "org",
    # User management
    "users_create": "users", "users_update": "users", "users_delete": "users",
    # Roles & permissions
    "role_create": "roles", "role_update": "roles", "role_delete": "roles",
}

# Modules that actually have edit actions (Roles screen offers View/Edit on them).
EDITABLE_MODULES = set(EDIT_ACTIONS.values())


# --------------------------------------------------------------------------
# Audit-log labels (no sensitive data is ever logged — just these labels)
# --------------------------------------------------------------------------

ACTION_LABELS = {
    "student_add": "Added an admission", "student_update": "Updated an admission",
    "student_delete": "Deleted an admission", "students_import": "Imported admissions",
    "agm_create": "Added an AGM", "agm_rename": "Renamed an AGM",
    "agm_delete": "Deleted an AGM", "agm_set_city": "Set an AGM's city",
    "exec_create": "Added a marketing exec", "exec_rename": "Renamed a marketing exec",
    "exec_delete": "Deleted a marketing exec",
    "campus_create": "Added a campus", "campus_rename": "Renamed a campus",
    "campus_delete": "Deleted a campus", "campus_set_city": "Set a campus's city",
    "city_create": "Added a city", "city_rename": "Renamed a city",
    "city_delete": "Deleted a city",
    "course_create": "Added a course", "course_rename": "Renamed a course",
    "course_delete": "Deleted a course",
    "users_create": "Created a user", "users_update": "Updated a user",
    "users_delete": "Deleted a user",
    "role_create": "Created a role", "role_update": "Updated a role",
    "role_delete": "Deleted a role",
}


def action_label(method):
    return ACTION_LABELS.get(method, (method or "").replace("_", " ").capitalize())
