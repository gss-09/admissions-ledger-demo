"""
The Api class: one method per front-end action. Each public method is reachable
as ``POST /api/<method>`` (see ``app.routes``).

Methods contain *logic only* — they call the data layer for SQL and the
permission layer for access decisions. The dispatcher has already enforced
authentication, the EDIT gate (for writes) and the VIEW gate (for the role
metadata reads) before any method here runs.

The class is composed from one mixin per domain (mirroring ``app/data/`` and
``web/js/screens/``); shared private helpers live on ``ApiBase``. Adding a public
method to any mixin adds an endpoint — register writes in ``config.EDIT_ACTIONS``.
"""

from app.endpoints._base import ApiBase
from app.endpoints.account import AccountApi
from app.endpoints.audit import AuditApi
from app.endpoints.auth import AuthApi
from app.endpoints.org import OrgApi
from app.endpoints.roles import RolesApi
from app.endpoints.students import StudentsApi
from app.endpoints.users import UsersApi


class Api(AuthApi, AccountApi, AuditApi, OrgApi, RolesApi, UsersApi,
          StudentsApi, ApiBase):
    pass
