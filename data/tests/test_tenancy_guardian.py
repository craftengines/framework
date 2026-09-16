"""TenantScopeGuardian: warn logs and proceeds, strict raises, jobs are exempt."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import logging

import pytest

from craft.orm.tenant_guardian import TenantScopeGuardian, TenantScopeUnboundError


def test_warn_mode_logs_and_does_not_raise(caplog):
    guardian = TenantScopeGuardian(mode="warn")
    with caplog.at_level(logging.WARNING, logger="craft"):
        guardian.check(context="request", tenant_id=None)
    assert any("no tenant bound" in record.message for record in caplog.records)


def test_warn_mode_is_silent_when_a_tenant_is_bound(caplog):
    guardian = TenantScopeGuardian(mode="warn")
    with caplog.at_level(logging.WARNING, logger="craft"):
        guardian.check(context="request", tenant_id="some-tenant-id")
    assert not caplog.records


def test_strict_mode_raises_when_no_tenant_is_bound():
    guardian = TenantScopeGuardian(mode="strict")
    with pytest.raises(TenantScopeUnboundError):
        guardian.check(context="request", tenant_id=None)


def test_strict_mode_does_not_raise_when_a_tenant_is_bound():
    guardian = TenantScopeGuardian(mode="strict")
    guardian.check(context="request", tenant_id="some-tenant-id")  # must not raise


@pytest.mark.parametrize("context", ["console", "job"])
def test_console_and_job_contexts_are_exempt_even_in_strict_mode(context):
    guardian = TenantScopeGuardian(mode="strict")
    guardian.check(context=context, tenant_id=None)  # must not raise


def test_scope_tenant_wires_the_configured_guardian_mode(migrated_database):
    """ScopeTenant.handle() reads database.tenancy.guardian_mode and applies it."""
    from craft.http.middleware import ScopeTenant

    config = migrated_database.make("config")
    original = config.get("database.tenancy.guardian_mode")
    config.set("database.tenancy.guardian_mode", "strict")
    try:
        middleware = ScopeTenant(app=migrated_database, require_isolation=False)
        middleware.resolve = lambda request, container: None

        class _Request:
            @staticmethod
            def header(name):
                return None

        with pytest.raises(TenantScopeUnboundError):
            middleware.handle(_Request(), lambda request: "never reached")
    finally:
        config.set("database.tenancy.guardian_mode", original)
