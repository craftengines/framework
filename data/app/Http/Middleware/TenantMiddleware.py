"""
TenantMiddleware — Routes each request to its tenant's isolated PostgreSQL schema.
Category: Middleware (HTTP Pipeline Layer).
Relations:
  - Resolves the current user through the Auth facade and scopes the DB facade
    to that user's schema for the rest of the request.
  - Registered globally in `bootstrap/app.py`, and only when
    `framework.MULTI_TENANCY_ENABLED` is on.
References:
  - Guide: `documentation/orm.md`
  - Skill: `craft-development` (`.agents/skills/framework/craft-development/SKILL.md`,
    workspace root, outside this repository)
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import logging
import re

from craft.facades import Auth, DB
from craft.http.middleware import Middleware

#: Warn once per process, not once per request — a tenant app under load would
#: otherwise write this line thousands of times a second.
_warned_about_isolation = False


class TenantIsolationUnavailable(RuntimeError):
    """The driver cannot provide the isolation this request needs."""

    status_code = 500


class TenantMiddleware(Middleware):
    """Scope the connection to the authenticated tenant's schema.

    The **schema** strategy: one PostgreSQL schema per tenant, selected with
    `search_path`. Still the right answer for a handful of tenants that need
    physical separation. For the general case prefer the row-level-security
    strategy — `ScopeTenant` in `engine/http/middleware.py` — which migrates
    once instead of once per tenant, keeps DDL off the request path, and is
    enforced by the database rather than by every query remembering to scope
    itself. Select it with `MULTI_TENANCY_STRATEGY=rls`.

    Schema isolation needs PostgreSQL. This used to warn once and keep serving
    on SQLite and MySQL, where `ensure_tenant_schema` is a no-op and every
    tenant therefore shares one set of tables. A warning is the wrong response
    to that: the request proceeds, the data crosses the boundary, and the only
    trace is a log line nobody reads until afterwards. It now refuses.
    """

    def handle(self, request, next_callable):
        user = Auth.user()

        if user is None or user.get_attribute("type") != "tenant":
            DB.set_tenant_schema(None)
            return next_callable(request)

        self._assert_isolation_is_real()

        user_id = user.get_attribute("id")
        schema_name = f"tenant_{re.sub(r'[^a-zA-Z0-9_]', '_', str(user_id).lower())}"

        DB.set_tenant_schema(schema_name)
        DB.ensure_tenant_schema(schema_name, user)

        return next_callable(request)

    @staticmethod
    def _assert_isolation_is_real():
        """Refuse to serve a tenant request the database will not isolate."""
        driver = getattr(DB, "driver", None)
        if driver == "postgresql":
            return

        global _warned_about_isolation
        if not _warned_about_isolation:
            _warned_about_isolation = True
            logging.getLogger("craft").error(
                "Refused a tenant request: the %r driver cannot isolate schemas, "
                "so every tenant would share the same tables. Use PostgreSQL, "
                "switch to MULTI_TENANCY_STRATEGY=rls, or turn off "
                "MULTI_TENANCY_ENABLED.", driver,
            )

        raise TenantIsolationUnavailable(
            f"Multi-tenancy is enabled and this request belongs to a tenant, but "
            f"the {driver!r} driver cannot isolate schemas — every tenant would "
            f"share the same tables. Use PostgreSQL, switch to "
            f"MULTI_TENANCY_STRATEGY=rls, or turn off MULTI_TENANCY_ENABLED."
        )
