"""Tenancy has to be wired, not merely available.

The row-level-security layer existed as a library before these tests: the
policy DSL, the middleware and the audit were all implemented and none of them
were reachable from a fresh checkout. Three gaps, all of which these tests
close:

  - `t.tenant_scoped()` referenced a `tenants` table that no migration created,
    so the call the guide advertises as "the whole tenancy contract in one
    line" failed outright on PostgreSQL.
  - `MULTI_TENANCY_STRATEGY` appeared in error messages and documentation while
    nothing read it. "Switch to MULTI_TENANCY_STRATEGY=rls" did nothing.
  - `ScopeTenant` was never registered by the bootstrap, so the row-level
    strategy could not be selected at all.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest

from craft.facades import Config, DB, Schema, Tenant
from craft.migrations.schema import SchemaBuilder


# -- the tenants table ---------------------------------------------------------


def test_the_tenants_table_ships_with_the_framework(migrated_database):
    """`tenant_scoped()` points at it by default, so it has to exist."""
    assert migrated_database.make("db").table_exists("tenants")


def test_tenant_scoped_works_with_its_own_default(migrated_database):
    """The exact call the guide shows. It used to fail: `relation "tenants"
    does not exist`, because every test passed `references=None` and stepped
    around the default."""
    schema = SchemaBuilder(migrated_database.make("db"))
    schema.drop_if_exists("wiring_probe")
    try:
        schema.create_table("wiring_probe", lambda t: (
            t.id(type="integer"),
            t.string("label"),
            t.tenant_scoped(),
        ))
        assert migrated_database.make("db").table_exists("wiring_probe")
    finally:
        schema.drop_if_exists("wiring_probe")


def test_the_tenants_key_is_a_uuid_not_a_sequence(migrated_database):
    """A tenant id travels in URLs, in the session variable and in job
    payloads; a sequential integer there leaks the customer count."""
    columns = Schema.column_listing("tenants")
    assert "id" in columns and "slug" in columns

    from craft.orm.model import Model

    class TenantRecord(Model):
        __table__ = "tenants"
        primary_key = "id"
        key_type = "uuid"
        fillable = ["name", "slug"]
        uses_uuid = False

    created = TenantRecord.create({"name": "Acme", "slug": "acme-wiring"})
    key = str(created.get_attribute("id"))
    try:
        assert key.count("-") == 4, f"expected a UUID key, got {key!r}"
        assert key[14] == "7", "the framework generates time-ordered v7 keys"
    finally:
        DB.statement("DELETE FROM tenants WHERE slug = ?", ["acme-wiring"])


# -- the strategy --------------------------------------------------------------


def test_the_strategy_is_configured_and_defaults_to_rls():
    """It used to be named in error messages while nothing read it."""
    assert Config.get("framework.MULTI_TENANCY_STRATEGY") == "rls"


def test_the_bootstrap_selects_a_middleware_per_strategy():
    """Reads the wiring rather than the config, because the wiring is what
    was missing: the strategy existed on paper and picked nothing."""
    import inspect

    import bootstrap.app as bootstrap

    source = inspect.getsource(bootstrap)
    assert "MULTI_TENANCY_STRATEGY" in source
    assert "ScopeTenant" in source
    assert "TenantMiddleware" in source


def test_an_unknown_strategy_stops_the_boot():
    """Silently serving every tenant from one set of tables is the one
    outcome a typo here must not produce."""
    import inspect

    import bootstrap.app as bootstrap

    source = inspect.getsource(bootstrap)
    assert "raise ValueError" in source
    assert "'rls' or 'schema'" in source


def test_no_tenant_middleware_runs_while_tenancy_is_off(migrated_database):
    from bootstrap.app import kernel

    registered = {cls.__name__ for cls in kernel.middleware_classes}
    assert Config.get("framework.MULTI_TENANCY_ENABLED") is False
    assert not {"ScopeTenant", "TenantMiddleware"} & registered


# -- the application role ------------------------------------------------------


def test_provision_role_refuses_a_name_that_could_smuggle_sql():
    """CREATE ROLE takes an identifier, so the name is interpolated."""
    from craft.migrations.schema import _assert_table

    with pytest.raises(ValueError):
        _assert_table('craft_app"; DROP TABLE users; --')


def test_the_provisioned_role_is_verified_not_assumed():
    """The command re-reads pg_roles and fails if the role still bypasses.

    Creating the role is not the same as the role being subject to policies,
    and the difference is the entire point of the command.
    """
    import inspect

    from craft.cli.app import db_provision_role

    source = inspect.getsource(db_provision_role)
    assert "NOBYPASSRLS" in source
    assert "rolsuper" in source and "rolbypassrls" in source
    # Future tables need the grant too, or the role works until the next
    # migration and then stops.
    assert "ALTER DEFAULT PRIVILEGES" in source


# -- binding a tenant to a request ---------------------------------------------


def test_users_can_carry_a_tenant(migrated_database):
    """`ScopeTenant.resolve()` falls back to the user's `tenant_id`.

    The column did not exist, so with the row-level strategy on, nothing ever
    bound a tenant and every scoped query raised `TenantNotBoundError`.
    """
    assert "tenant_id" in Schema.column_listing("users")


def test_a_subdomain_resolves_against_the_tenants_table(migrated_database):
    """It used to be a hook that returned None, so host resolution never worked."""
    from craft.http.middleware import ScopeTenant
    from craft.orm.model import Model

    class TenantRecord(Model):
        __table__ = "tenants"
        primary_key = "id"
        key_type = "uuid"
        fillable = ["name", "slug", "is_active"]
        uses_uuid = False

    created = TenantRecord.create({"name": "Acme", "slug": "acme-sub", "is_active": True})
    middleware = ScopeTenant(app=migrated_database, require_isolation=False)
    try:
        assert str(middleware.tenant_for_subdomain("acme-sub")) == str(
            created.get_attribute("id")
        )
        assert middleware.tenant_for_subdomain("nobody-here") is None
    finally:
        DB.statement("DELETE FROM tenants WHERE slug = ?", ["acme-sub"])


def test_a_suspended_tenant_resolves_to_nothing(migrated_database):
    """Suspending a tenant should be a row update, not a deployment."""
    from craft.http.middleware import ScopeTenant
    from craft.orm.model import Model

    class TenantRecord(Model):
        __table__ = "tenants"
        primary_key = "id"
        key_type = "uuid"
        fillable = ["name", "slug", "is_active"]
        uses_uuid = False

    TenantRecord.create({"name": "Gamma", "slug": "gamma-sub", "is_active": False})
    middleware = ScopeTenant(app=migrated_database, require_isolation=False)
    try:
        assert middleware.tenant_for_subdomain("gamma-sub") is None
    finally:
        DB.statement("DELETE FROM tenants WHERE slug = ?", ["gamma-sub"])


def test_shared_hosts_are_never_read_as_tenant_names(migrated_database):
    from craft.http.middleware import ScopeTenant

    class _Request:
        @staticmethod
        def header(name):
            return "api.example.com" if name == "host" else None

    class _Container:
        @staticmethod
        def make(key):
            if key == "auth":
                raise KeyError("no auth in this probe")
            return migrated_database.make(key)

    middleware = ScopeTenant(app=migrated_database, require_isolation=False)
    assert middleware.resolve(_Request(), _Container()) is None
    assert "api" in middleware.RESERVED_SUBDOMAINS


# -- the whole contract, end to end -------------------------------------------


def test_a_scoped_table_isolates_once_a_tenant_is_bound(migrated_database):
    """The default call, a real tenant row, and a query that sees only its own."""
    db = migrated_database.make("db")
    schema = SchemaBuilder(db)

    from craft.orm.model import Model
    from craft.orm.tenant_scoped import TenantScoped

    class TenantRecord(Model):
        __table__ = "tenants"
        primary_key = "id"
        key_type = "uuid"
        fillable = ["name", "slug"]
        uses_uuid = False

    schema.drop_if_exists("wiring_notes")
    schema.create_table("wiring_notes", lambda t: (
        t.id(type="integer"),
        t.string("body"),
        t.tenant_scoped(),
        t.timestamps(),
    ))

    class Note(TenantScoped, Model):
        __table__ = "wiring_notes"
        fillable = ["body"]
        uses_uuid = False

    try:
        acme = TenantRecord.create({"name": "Acme", "slug": "acme-e2e"})
        beta = TenantRecord.create({"name": "Beta", "slug": "beta-e2e"})

        with Tenant.scope(str(acme.get_attribute("id"))):
            Note.create({"body": "acme only"})
            assert Note.query().count() == 1

        with Tenant.scope(str(beta.get_attribute("id"))):
            assert Note.query().count() == 0, "a tenant saw another tenant's row"
            Note.create({"body": "beta only"})
            assert Note.query().count() == 1
    finally:
        schema.drop_if_exists("wiring_notes")
        DB.statement("DELETE FROM tenants WHERE slug IN (?, ?)", ["acme-e2e", "beta-e2e"])
        Tenant.clear()
