"""Tenant scoping mixin for the Craft ORM.

Row-level security is the enforcement; this mixin is the ergonomics. It fills
`tenant_id` on write, adds the predicate the planner needs to use a
tenant-leading index, and makes cross-tenant access something a developer has
to type on purpose.

Category: Core Framework (ORM).
Relations:
  - Mixed in before `Model` in a subclass's bases — list order matters, or the
    MRO makes `Model` win (`class Invoice(TenantScoped, Model)`).
  - Reads the bound tenant from `engine/orm/tenancy.py`.
References:
  - Guide: `documentation/orm.md#multi-tenancy`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from typing import Any, Dict


class TenantScoped:
    """Model mixin for a table under a tenant isolation policy.

    List it FIRST, the same way `SoftDeletes` must be::

        class Invoice(TenantScoped, Model):
            __table__ = "invoices"

    The `where` clause this adds is **not** the isolation boundary — the policy
    in the database is. It is here for two reasons: the planner needs a
    `tenant_id` predicate to pick a tenant-leading index, and a suite running on
    SQLite (which has no row-level security) still fails a cross-tenant
    assertion instead of quietly passing.
    """

    tenant_column: str = "tenant_id"

    def __init_subclass__(cls, **kwargs):
        """Refuse the base order that silently removes the scope.

        With `class Invoice(Model, TenantScoped)` the MRO gives `Model.query()`,
        so every query runs unscoped while the model advertises tenant scoping.
        On SQLite that is a cross-tenant read with no error at all; on
        PostgreSQL the policy still holds, but the index predicate is gone and
        the failure becomes a performance mystery. Too quiet either way to leave
        as a documentation footnote.
        """
        super().__init_subclass__(**kwargs)

        mro = cls.__mro__
        model_class = next((base for base in mro if base.__name__ == "Model"), None)
        if model_class is None:
            return

        if mro.index(model_class) < mro.index(TenantScoped):
            raise TypeError(
                f"{cls.__name__} lists TenantScoped after Model, so Model.query() "
                f"wins the MRO and queries run unscoped. Write "
                f"`class {cls.__name__}(TenantScoped, Model)` instead."
            )

    # -- query scopes ----------------------------------------------------------

    @classmethod
    def _base_query(cls) -> Any:
        from engine.orm.query_builder import QueryBuilder

        return QueryBuilder(model_class=cls)

    @classmethod
    def query(cls) -> Any:
        """Scoped to the bound tenant. Raises if there is none."""
        from engine.orm.tenancy import TenantManager

        return cls._base_query().where(cls.tenant_column, TenantManager().id_or_fail())

    @classmethod
    def across_tenants(cls) -> Any:
        """Unscoped query, for admin and reporting paths.

        On PostgreSQL this still only reaches rows the connection's role may
        see: policies are created with FORCE ROW LEVEL SECURITY, so even the
        table owner is filtered. It is genuinely cross-tenant only under a role
        granted BYPASSRLS on purpose — which is the point, because that grant is
        auditable and this method call is grep-able.
        """
        return cls._base_query()

    # -- writes ----------------------------------------------------------------

    @classmethod
    def force_create(cls, attributes: Dict[str, Any]) -> Any:
        """Stamp the tenant on insert, so callers never have to remember it.

        An explicit `tenant_id` in `attributes` wins — a data importer moving
        rows between tenants is a real use — but the policy's WITH CHECK clause
        still refuses a value that is not the bound tenant, so this cannot be
        used to write into somebody else's data.
        """
        from engine.orm.tenancy import TenantManager

        attributes = dict(attributes)
        attributes.setdefault(cls.tenant_column, TenantManager().id_or_fail())
        return super().force_create(attributes)


__all__ = ["TenantScoped"]
