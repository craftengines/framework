"""The out-of-the-box experience for a single-tenant application.

Craft is meant to carry a personal side-project and a commercial multi-tenant
product equally well, and those two want opposite defaults. The resolution is
that multi-tenancy is off until asked for: a fresh checkout on SQLite runs
without a tenant boundary it cannot enforce, and turning the flag on is the
deliberate act that makes refusing an unisolatable request correct rather than
a surprise.

These tests exist because the failure they describe was shipped once. The
default was on, the seeder creates a `type = "tenant"` user, and SQLite cannot
isolate anything — so the demo worked right up until somebody signed in as that
user.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest

from app.Http.Middleware.TenantMiddleware import (
    TenantIsolationUnavailable,
    TenantMiddleware,
)
from craft.facades import Auth, Config


class _TenantUser:
    """The shape `UserSeeder` creates for the tenant demo account."""

    @staticmethod
    def get_attribute(name):
        return {"type": "tenant", "id": 2}.get(name)


class _PlainUser:
    @staticmethod
    def get_attribute(name):
        return {"type": "user", "id": 1}.get(name)


@pytest.fixture(autouse=True)
def _no_authenticated_user():
    yield
    Auth.set_user(None)


def test_multi_tenancy_is_off_until_it_is_asked_for(migrated_database):
    """A personal application should not acquire a tenant boundary by accident."""
    assert Config.get("framework.MULTI_TENANCY_ENABLED") is False


def test_the_tenant_middleware_is_not_registered_by_default(migrated_database):
    """Nothing pays for per-request tenant resolution it never wanted."""
    from bootstrap.app import kernel

    registered = {cls.__name__ for cls in kernel.middleware_classes}
    assert "TenantMiddleware" not in registered
    assert "ScopeTenant" not in registered


def test_a_seeded_tenant_user_does_not_break_a_sqlite_checkout(migrated_database):
    """The exact path that used to 500: the demo tenant account on SQLite.

    With the flag off the middleware is not in the stack at all, so the request
    is served. This asserts the middleware itself stays inert for a
    non-tenant user, which is the other half of the same guarantee.
    """
    Auth.set_user(_PlainUser())
    assert TenantMiddleware().handle(object(), lambda request: "served") == "served"


def test_enabling_it_on_a_driver_that_cannot_isolate_refuses(migrated_database):
    """And once it *is* asked for, the refusal is the correct answer.

    A warning was the old behaviour and the wrong one: the request proceeded,
    the data crossed the boundary, and the only trace was a log line read after
    the fact.
    """
    if migrated_database.make("db").dialect.supports("rls"):
        pytest.skip("this driver isolates; the refusal path needs one that cannot")

    Auth.set_user(_TenantUser())
    with pytest.raises(TenantIsolationUnavailable) as excinfo:
        TenantMiddleware().handle(object(), lambda request: "served")

    message = str(excinfo.value)
    # The refusal has to name every way out, or it is just an obstacle.
    assert "PostgreSQL" in message
    assert "MULTI_TENANCY_STRATEGY=rls" in message
    assert "MULTI_TENANCY_ENABLED" in message
