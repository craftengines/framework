"""Tests for tenant scoping and row-level security.

Phase 3 of the PostgreSQL-native data layer. Two kinds of assertion live here:

  - Ones that hold on every driver — the context binding, the `TenantScoped`
    mixin's scoping and MRO guard, and the generated DDL.
  - Ones that need a real policy engine, marked `postgres_only`. On SQLite the
    isolation is the mixin's `where` clause, which is why `ScopeTenant` refuses
    to serve tenant traffic there at all.

The pool-bleed test is the one that matters most: a session variable lives on
the physical connection, so a connection returned to the pool still carrying a
tenant hands the next borrower another customer's rows.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import threading

import pytest

from craft.facades import DB, Tenant
from craft.migrations.schema import Blueprint, Grammar, SchemaBuilder
from craft.orm.dialect import UnsupportedFeatureError
from craft.orm.model import Model
from craft.orm.tenancy import TenantManager, TenantNotBoundError, current_tenant_id
from craft.orm.tenant_scoped import TenantScoped

ACME = "11111111-1111-1111-1111-111111111111"
BETA = "22222222-2222-2222-2222-222222222222"

postgres_only = pytest.mark.skipif(
    "config.getoption('--co', default=False)", reason="collection only"
)


@pytest.fixture(autouse=True)
def unbound():
    """Every test starts and ends with no tenant bound."""
    Tenant.clear()
    yield
    Tenant.clear()


@pytest.fixture
def invoices_table(migrated_database):
    schema = SchemaBuilder(migrated_database.make("db"))
    schema.drop_if_exists("tenant_invoices")
    schema.create_table("tenant_invoices", lambda t: (
        t.id(type="integer"),
        t.string("reference"),
        t.tenant_scoped(references=None),
        t.timestamps(),
    ))
    yield "tenant_invoices"
    schema.drop_if_exists("tenant_invoices")


class Invoice(TenantScoped, Model):
    __table__ = "tenant_invoices"
    fillable = ["reference"]
    uses_uuid = False


# -- the context binding -------------------------------------------------------


def test_nothing_is_bound_by_default():
    assert current_tenant_id() is None
    assert Tenant.id() is None


def test_binding_is_readable_through_the_facade_and_the_module():
    Tenant.bind(ACME)
    assert Tenant.id() == ACME
    assert current_tenant_id() == ACME


def test_id_or_fail_names_the_fix():
    with pytest.raises(TenantNotBoundError) as excinfo:
        TenantManager().id_or_fail()
    assert "Tenant.scope" in str(excinfo.value)


def test_scope_restores_the_previous_tenant_not_none():
    """An admin task iterating tenants must come back out where it started."""
    Tenant.bind(ACME)

    with Tenant.scope(BETA):
        assert Tenant.id() == BETA
        with Tenant.scope(ACME):
            assert Tenant.id() == ACME
        assert Tenant.id() == BETA

    assert Tenant.id() == ACME


def test_scope_restores_even_when_the_block_raises():
    Tenant.bind(ACME)
    with pytest.raises(ValueError):
        with Tenant.scope(BETA):
            raise ValueError("boom")
    assert Tenant.id() == ACME


def test_a_thread_does_not_inherit_another_threads_tenant():
    """ContextVar isolation is what makes per-request binding safe."""
    Tenant.bind(ACME)
    seen = {}

    def worker():
        seen["before"] = current_tenant_id()
        Tenant.bind(BETA)
        seen["after"] = current_tenant_id()

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()

    assert seen["before"] is None, "a fresh thread must start unbound"
    assert seen["after"] == BETA
    assert Tenant.id() == ACME, "the worker's binding must not escape its thread"


# -- the model mixin -----------------------------------------------------------


def test_a_scoped_query_refuses_to_build_with_nothing_bound():
    with pytest.raises(TenantNotBoundError):
        Invoice.query()


def test_a_scoped_query_carries_the_tenant_predicate():
    Tenant.bind(ACME)
    sql, params = Invoice.query().to_sql()

    assert "tenant_id = ?" in sql
    assert params == [ACME]


def test_across_tenants_drops_the_predicate():
    Tenant.bind(ACME)
    sql, params = Invoice.across_tenants().to_sql()

    assert "tenant_id" not in sql
    assert params == []


def test_the_tenant_is_stamped_on_insert(invoices_table):
    Tenant.bind(ACME)
    invoice = Invoice.create({"reference": "INV-1"})

    assert invoice.get_attribute("tenant_id") == ACME


def test_a_query_sees_only_its_own_tenants_rows(invoices_table):
    with Tenant.scope(ACME):
        Invoice.create({"reference": "acme-1"})
        Invoice.create({"reference": "acme-2"})
    with Tenant.scope(BETA):
        Invoice.create({"reference": "beta-1"})

    with Tenant.scope(ACME):
        assert Invoice.query().count() == 2
    with Tenant.scope(BETA):
        assert Invoice.query().count() == 1

    Tenant.bind(ACME)
    assert Invoice.across_tenants().count() == 3


def test_the_mro_guard_refuses_the_order_that_removes_the_scope():
    with pytest.raises(TypeError, match="lists TenantScoped after Model"):
        class Broken(Model, TenantScoped):
            __table__ = "tenant_invoices"


# -- generated DDL -------------------------------------------------------------


def test_tenant_scoped_adds_the_column_the_index_and_the_policy():
    blueprint = Blueprint("invoices")
    blueprint.id(type="integer")
    blueprint.tenant_scoped(references=None)

    assert [c.name for c in blueprint.columns] == ["id", "tenant_id"]
    assert blueprint.indexes[0]["columns"] == ["tenant_id"]
    assert blueprint.rls["force"] is True
    assert blueprint.rls["policy"] == "invoices_tenant_isolation"


def test_the_policy_is_forced_and_fails_closed():
    blueprint = Blueprint("invoices")
    blueprint.id(type="integer")
    blueprint.tenant_scoped(references=None)
    sql = "\n".join(Grammar("postgresql").compile_create(blueprint))

    assert 'ALTER TABLE "invoices" ENABLE ROW LEVEL SECURITY' in sql
    # Without FORCE the policy does not apply to the table's owner, and
    # migrations run as the owner.
    assert 'ALTER TABLE "invoices" FORCE ROW LEVEL SECURITY' in sql
    # NULLIF turns a cleared session variable into NULL, and NULL matches
    # nothing — an unbound connection reads no rows rather than all of them.
    assert "NULLIF(current_setting('app.current_tenant_id', true), '')" in sql
    # Reads and writes both, or a tenant could insert a row it cannot read back.
    assert "USING (" in sql and "WITH CHECK (" in sql


def test_no_policy_ddl_is_emitted_where_there_is_no_policy_engine():
    blueprint = Blueprint("invoices")
    blueprint.tenant_scoped(references=None)

    assert Grammar("sqlite").compile_rls(blueprint) == []
    assert Grammar("mysql").compile_rls(blueprint) == []


def test_a_policy_name_cannot_smuggle_sql(migrated_database):
    schema = SchemaBuilder(migrated_database.make("db"))
    with pytest.raises(ValueError):
        schema.drop_policy("invoices", 'x" ON invoices; DROP TABLE users; --')


# -- the connection contract ---------------------------------------------------


def test_set_config_is_used_because_set_local_cannot_be_bound():
    """The GUC is set through a function call, never string interpolation.

    `SET LOCAL app.current_tenant_id = :id` is not parameterizable, so the
    value would have to be interpolated — from request input, into SQL.
    """
    from craft.orm.connection import Connection

    executed = []

    class _Cursor:
        def execute(self, sql, params=None):
            executed.append((sql, params))

        def close(self):
            pass

    class _Pdo:
        @staticmethod
        def cursor():
            return _Cursor()

        @staticmethod
        def commit():
            pass

    connection = Connection({"driver": "pgsql"})
    hostile = "x'; DROP TABLE users; --"
    connection._set_tenant(_Pdo(), hostile, local=True)

    sql, params = executed[-1]
    assert "set_config" in sql
    # The value reaches the driver as a binding. Nothing of it is in the SQL.
    assert hostile not in sql
    assert "DROP TABLE" not in sql
    assert hostile in params


def test_the_guc_is_namespaced():
    from craft.orm.connection import Connection

    # PostgreSQL only accepts a custom setting under a prefix it does not own.
    assert "." in Connection.TENANT_GUC


def test_release_forgets_the_tenant(migrated_database):
    """The pool must hand out a connection with no tenant on it.

    This is the failure the whole design turns on: a session variable lives on
    the *physical* connection, so one left set is read by whoever borrows it
    next — correctly, invisibly, and as another customer's data.
    """
    connection = migrated_database.make("db").write_connection
    connection.use_tenant(ACME)
    assert connection.tenant == ACME

    connection.release()
    assert connection.tenant is None
    assert connection._session().applied_tenant is None


def test_the_manager_clears_the_tenant_on_release(migrated_database):
    db = migrated_database.make("db")
    Tenant.bind(ACME)
    db.release()
    assert db.write_connection.tenant is None


# -- enforcement ---------------------------------------------------------------


def test_enforcement_reports_whether_the_role_is_actually_subject_to_policies(
    migrated_database,
):
    """A policy that cannot apply to the connecting role is decoration.

    Superusers bypass row-level security outright, and so do roles granted
    BYPASSRLS — `FORCE ROW LEVEL SECURITY` reaches the table's *owner*, not
    either of those. So `relrowsecurity` and `relforcerowsecurity` can both be
    true, the policy can be correct, and every tenant's rows still come back to
    everyone. Only the catalogue knows.
    """
    from craft.orm.tenancy import TenantManager

    manager = TenantManager(migrated_database)
    status = manager.enforcement(refresh=True)

    assert set(status) == {"role", "enforced", "reason"}
    if not status["enforced"]:
        assert status["reason"], "a refusal must say why"


def test_assert_enforced_refuses_a_role_that_bypasses(migrated_database):
    from craft.orm.tenancy import TenantIsolationError, TenantManager

    manager = TenantManager(migrated_database)
    if manager.enforcement(refresh=True)["enforced"]:
        pytest.skip("this role is subject to policies; the refusal path needs one that is not")

    with pytest.raises(TenantIsolationError) as excinfo:
        manager.assert_enforced()
    assert "BYPASSRLS" in str(excinfo.value) or "superuser" in str(excinfo.value)


def test_the_policy_really_filters_under_a_non_bypassing_role(migrated_database):
    """The assertion the whole design turns on, against a real policy engine.

    Run under a purpose-made role that is neither superuser, nor BYPASSRLS, nor
    the table owner — because under any of those the query returns everything
    and the test would pass for the wrong reason.
    """
    db = migrated_database.make("db")
    if not db.dialect.supports("rls"):
        pytest.skip("this driver has no row-level security")

    from craft.migrations.schema import SchemaBuilder
    from craft.orm.db import DatabaseManager

    schema = SchemaBuilder(db)
    schema.drop_if_exists("rls_probe")
    schema.create_table("rls_probe", lambda t: (
        t.id(type="integer"),
        t.string("ref"),
        t.tenant_scoped(references=None),
    ))

    config = dict(_connection_config(migrated_database))
    role, password = "craft_rls_probe", "probe-secret"

    try:
        db.statement(f"DROP OWNED BY {role}")
    except Exception:
        pass
    try:
        db.statement(f"DROP ROLE IF EXISTS {role}")
    except Exception:
        pass
    try:
        db.statement(f"CREATE ROLE {role} LOGIN PASSWORD '{password}' NOBYPASSRLS")
        db.statement(f"GRANT USAGE ON SCHEMA public TO {role}")
        db.statement(f"GRANT SELECT, INSERT ON rls_probe TO {role}")
    except Exception as exc:
        pytest.skip(f"cannot create a test role here: {exc}")

    db.statement("INSERT INTO rls_probe (ref, tenant_id) VALUES (?, ?)", ["acme", ACME])
    db.statement("INSERT INTO rls_probe (ref, tenant_id) VALUES (?, ?)", ["beta", BETA])

    scoped = DatabaseManager(config={**config, "username": role, "password": password})
    try:
        from craft.orm.tenancy import TenantManager

        as_role = TenantManager(_ContainerFor(scoped))
        assert as_role.enforcement(refresh=True)["enforced"] is True

        as_role.bind(ACME)
        rows = scoped.select("SELECT ref FROM rls_probe")
        assert [r["ref"] for r in rows] == ["acme"], "the policy did not filter"

        as_role.bind(BETA)
        assert [r["ref"] for r in scoped.select("SELECT ref FROM rls_probe")] == ["beta"]

        # And with nothing bound: no rows, not all of them. Fail-closed is the
        # property that makes a forgotten scope harmless instead of a breach.
        as_role.clear()
        assert scoped.select("SELECT ref FROM rls_probe") == []
    finally:
        scoped.purge()
        TenantManager._enforcement = None
        schema.drop_if_exists("rls_probe")
        try:
            db.statement(f"DROP OWNED BY {role}")
            db.statement(f"DROP ROLE IF EXISTS {role}")
        except Exception:
            pass


def _connection_config(app) -> dict:
    config = app.make("config")
    name = config.get("database.default")
    return config.get(f"database.connections.{name}") or {}


class _ContainerFor:
    """Container shim exposing one specific database manager as `db`."""

    def __init__(self, db):
        self._db = db

    def make(self, key):
        if key == "db":
            return self._db
        raise KeyError(key)


# -- middleware ----------------------------------------------------------------


def test_scope_tenant_refuses_a_driver_without_isolation(migrated_database):
    from craft.http.middleware import ScopeTenant

    middleware = ScopeTenant(app=migrated_database)
    if migrated_database.make("db").dialect.supports("rls"):
        pytest.skip("this driver does isolate; the refusal path needs one that cannot")

    with pytest.raises(UnsupportedFeatureError):
        middleware.handle(_FakeRequest(), lambda request: "never reached")


def test_scope_tenant_can_opt_out_explicitly(migrated_database):
    from craft.http.middleware import ScopeTenant

    middleware = ScopeTenant(app=migrated_database, require_isolation=False)
    assert middleware.handle(_FakeRequest(), lambda request: "ok") == "ok"


def test_scope_tenant_resolves_from_the_authenticated_user(migrated_database):
    from craft.http.middleware import ScopeTenant

    class _User:
        @staticmethod
        def get_attribute(name):
            return ACME if name == "tenant_id" else None

    class _Auth:
        @staticmethod
        def user():
            return _User()

    class _Container:
        @staticmethod
        def make(key):
            return _Auth() if key == "auth" else migrated_database.make(key)

    middleware = ScopeTenant(app=migrated_database, require_isolation=False)
    assert middleware.resolve(_FakeRequest(), _Container()) == ACME


class _FakeRequest:
    @staticmethod
    def header(name):
        return "" if name == "host" else None
