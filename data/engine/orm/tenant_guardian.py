"""Second-layer check for a request proceeding with no tenant bound.

Row-level security is the enforcement; `TenantScoped`'s own `where` is the
first application-level safety net. This is a third, narrower one: a request
that reaches the point tenancy should already be resolved, with nothing
bound, is either a bug in tenant resolution or a route that legitimately runs
outside any tenant (a health check, a public marketing page). The guardian
cannot tell those apart on its own, so it logs by default (`warn`) and only
refuses outright (`strict`) once an operator has confirmed every request path
does bind one.

Category: Core Framework (ORM).
Relations:
  - Wired into `ScopeTenant.handle()` (`engine/http/middleware.py`), after
    `tenant.bind(...)`.
  - Configured via `database.tenancy.guardian_mode`
    (`config/database.py`, `TENANCY_GUARDIAN_MODE`).
References:
  - Plan: `.claude/plans/slice-1-data-integrity-and-tenant-isolation.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import logging
from typing import Literal

GuardianMode = Literal["warn", "strict"]

#: Contexts the guardian never checks: a migration, a queue worker or a CLI
#: command binds its own tenant explicitly (or deliberately runs across all
#: of them), so "no tenant bound yet" there is not a resolution failure.
_EXEMPT_CONTEXTS = frozenset({"console", "job"})


class TenantScopeUnboundError(RuntimeError):
    """Strict mode: a request context proceeded with no tenant bound."""

    code = "TENANT_SCOPE_UNBOUND"
    message_key = "tenancy.guardian.unbound"


class TenantScopeGuardian:
    """Warns or refuses when a request-context operation has no tenant bound."""

    def __init__(self, mode: GuardianMode = "warn") -> None:
        """Build the guardian.

        Args:
            mode: `"warn"` logs and continues; `"strict"` raises.
        """
        self.mode = mode

    def check(self, *, context: str, tenant_id: object) -> None:
        """Verify a tenant is bound for a non-exempt context.

        Args:
            context: `"request"` for an ordinary HTTP request; `"console"` or
                `"job"` for CLI/queue work, which is exempt.
            tenant_id: The currently bound tenant id, or `None`.

        Raises:
            TenantScopeUnboundError: `mode` is `"strict"`, the context is not
                exempt, and no tenant is bound.
        """
        if context in _EXEMPT_CONTEXTS or tenant_id is not None:
            return

        message = f"a {context!r} context proceeded with no tenant bound"
        if self.mode == "strict":
            raise TenantScopeUnboundError(message)
        logging.getLogger("craft").warning(message)


__all__ = ["TenantScopeGuardian", "TenantScopeUnboundError"]
