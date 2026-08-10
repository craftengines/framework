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


class TenantMiddleware(Middleware):
    """Scope the connection to the authenticated tenant's schema.

    Schema isolation needs PostgreSQL. On SQLite and MySQL `ensure_tenant_schema`
    is a documented no-op so the middleware can run unchanged in development and
    tests — but that means every tenant shares one set of tables. Silently, that
    is a data-isolation failure wearing the costume of a working feature, so the
    first time it happens the framework says so.
    """

    def handle(self, request, next_callable):
        user = Auth.user()

        if user is None or user.get_attribute("type") != "tenant":
            DB.set_tenant_schema(None)
            return next_callable(request)

        user_id = user.get_attribute("id")
        schema_name = f"tenant_{re.sub(r'[^a-zA-Z0-9_]', '_', str(user_id).lower())}"

        DB.set_tenant_schema(schema_name)
        DB.ensure_tenant_schema(schema_name, user)

        self._warn_if_isolation_is_not_real()
        return next_callable(request)

    @staticmethod
    def _warn_if_isolation_is_not_real():
        global _warned_about_isolation
        if _warned_about_isolation:
            return

        driver = getattr(DB, "driver", None)
        if driver and driver != "postgresql":
            _warned_about_isolation = True
            logging.getLogger("craft").warning(
                "Multi-tenancy is enabled and a tenant request was served, but "
                "the %r driver cannot isolate schemas — every tenant is sharing "
                "the same tables. Use PostgreSQL, or turn off "
                "MULTI_TENANCY_ENABLED.", driver,
            )
