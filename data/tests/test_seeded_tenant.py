"""The seeded tenant account has to be a coherent account.

`UserSeeder` creates `tenant@craft.local` with `type = "tenant"`. Before this,
that user belonged to no tenant and the `tenants` table was empty, so turning
multi-tenancy on produced an account whose every scoped query raised
`TenantNotBoundError` — nothing resolved a tenant for it, by host or by user.

Seeding a user whose own configuration cannot work is worse than seeding
nothing, because it looks finished.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest

from craft.facades import DB
from database.seeders.UserSeeder import UserSeeder


@pytest.fixture
def seeded(migrated_database):
    """Run the seeder against a clean slate, and clean up after."""
    DB.statement("DELETE FROM users WHERE email LIKE ?", ["%@craft.local"])
    DB.statement("DELETE FROM tenants WHERE id = ?", [UserSeeder.DEMO_TENANT_ID])
    UserSeeder().run()
    yield
    DB.statement("DELETE FROM users WHERE email LIKE ?", ["%@craft.local"])
    DB.statement("DELETE FROM tenants WHERE id = ?", [UserSeeder.DEMO_TENANT_ID])


def test_the_demo_tenant_is_seeded(seeded):
    row = DB.select_one("SELECT name, slug, is_active FROM tenants WHERE id = ?",
                        [UserSeeder.DEMO_TENANT_ID])
    assert row is not None, "the tenant user has nothing to belong to"
    assert row["slug"] == UserSeeder.DEMO_TENANT_SLUG
    assert row["is_active"] in (True, 1)


def test_the_tenant_user_belongs_to_it(seeded):
    row = DB.select_one("SELECT type, tenant_id FROM users WHERE email = ?",
                        ["tenant@craft.local"])
    assert row["type"] == "tenant"
    assert str(row["tenant_id"]) == UserSeeder.DEMO_TENANT_ID


def test_the_other_demo_accounts_belong_to_no_tenant(seeded):
    """An operator and a plain user are not tenant-scoped, and must not be."""
    for email in ("user@craft.local", "admin@craft.local"):
        row = DB.select_one("SELECT tenant_id FROM users WHERE email = ?", [email])
        assert row["tenant_id"] is None, f"{email} should not belong to a tenant"


def test_the_seeder_is_idempotent(seeded):
    """Seeding twice must not duplicate the tenant — re-seeding is routine."""
    UserSeeder().seed_demo_tenant()
    UserSeeder().seed_demo_tenant()

    row = DB.select_one("SELECT COUNT(*) AS total FROM tenants WHERE id = ?",
                        [UserSeeder.DEMO_TENANT_ID])
    assert int(row["total"]) == 1


def test_the_demo_tenant_id_is_a_valid_uuid7(seeded):
    """It is a literal, so nothing generates it — it still has to be well formed,
    or a `uuid` column rejects it on PostgreSQL."""
    import uuid

    parsed = uuid.UUID(UserSeeder.DEMO_TENANT_ID)
    assert parsed.version == 7
    assert str(parsed) == UserSeeder.DEMO_TENANT_ID


def test_the_seeded_tenant_resolves_by_subdomain(seeded, migrated_database):
    """End of the chain: the host `acme.example.com` finds this tenant."""
    from craft.http.middleware import ScopeTenant

    middleware = ScopeTenant(app=migrated_database, require_isolation=False)
    resolved = middleware.tenant_for_subdomain(UserSeeder.DEMO_TENANT_SLUG)
    assert str(resolved) == UserSeeder.DEMO_TENANT_ID


def test_a_request_on_the_tenant_host_binds_it_for_the_whole_request(
    seeded, migrated_database
):
    """The middleware's actual job, not just its resolver.

    Everything else here checks that a tenant can be *found*. This checks that
    handling a request leaves it *bound*, which is what every scoped query and
    every generated policy then reads.
    """
    from craft.facades import Tenant
    from craft.http.middleware import ScopeTenant

    class _Request:
        @staticmethod
        def header(name):
            return "acme.example.com" if name == "host" else None

    Tenant.clear()
    seen = {}

    def _next(request):
        seen["bound"] = Tenant.id()
        return "served"

    middleware = ScopeTenant(app=migrated_database, require_isolation=False)
    try:
        assert middleware.handle(_Request(), _next) == "served"
        assert str(seen["bound"]) == UserSeeder.DEMO_TENANT_ID
    finally:
        Tenant.clear()
        migrated_database.make("db").release()


def test_an_unknown_host_leaves_no_tenant_bound(seeded, migrated_database):
    """Fail closed: an unrecognised host must not inherit whatever was bound."""
    from craft.facades import Tenant
    from craft.http.middleware import ScopeTenant

    class _Request:
        @staticmethod
        def header(name):
            return "nobody.example.com" if name == "host" else None

    class _Container:
        @staticmethod
        def make(key):
            if key == "auth":
                raise KeyError("nobody is authenticated")
            return migrated_database.make(key)

    Tenant.bind(UserSeeder.DEMO_TENANT_ID)
    seen = {}
    middleware = ScopeTenant(app=migrated_database, require_isolation=False)
    middleware.resolve = lambda request, container: ScopeTenant.resolve(
        middleware, request, _Container()
    )
    try:
        middleware.handle(_Request(), lambda r: seen.setdefault("bound", Tenant.id()))
        assert seen["bound"] is None, "a stale tenant survived into the next request"
    finally:
        Tenant.clear()
        migrated_database.make("db").release()


def test_the_seeded_tenant_resolves_from_the_authenticated_user(seeded, migrated_database):
    """And the other half: no useful host, so fall back to the user's own tenant."""
    from craft.http.middleware import ScopeTenant

    class _User:
        @staticmethod
        def get_attribute(name):
            row = DB.select_one("SELECT tenant_id FROM users WHERE email = ?",
                                ["tenant@craft.local"])
            return row["tenant_id"] if name == "tenant_id" else None

    class _Auth:
        @staticmethod
        def user():
            return _User()

    class _Container:
        @staticmethod
        def make(key):
            return _Auth() if key == "auth" else migrated_database.make(key)

    class _Request:
        @staticmethod
        def header(name):
            return "www.example.com" if name == "host" else None

    middleware = ScopeTenant(app=migrated_database, require_isolation=False)
    resolved = middleware.resolve(_Request(), _Container())
    assert str(resolved) == UserSeeder.DEMO_TENANT_ID
