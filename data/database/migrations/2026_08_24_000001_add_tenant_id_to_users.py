"""Migration: users belong to a tenant.

`ScopeTenant.resolve()` falls back to the authenticated user's `tenant_id`
after the host, and the column did not exist — so with the row-level strategy
enabled, nothing ever bound a tenant and every `TenantScoped` query raised
`TenantNotBoundError`. The isolation was wired end to end except for the one
column that says which tenant a person belongs to.

Nullable on purpose: an operator, a support account and every user of a
single-tenant application belong to no tenant, and `NOT NULL` here would make
those unrepresentable.

Category: Framework schema (multi-tenancy).
References:
  - Guide: `documentation/postgres.md#binding-a-tenant`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.facades import DB, Schema


def up():
    Schema.table("users", lambda t: (
        t.uuid("tenant_id").nullable(),
        t.index_on(["tenant_id"], name="idx_users_tenant_id"),
    ))

    if not DB.dialect.supports("rls"):
        # `ALTER TABLE ... ADD COLUMN` carries no REFERENCES clause in the
        # portable grammar, and SQLite cannot add a foreign key to an existing
        # table at all. The column still works; it just is not enforced there.
        return

    Schema.raw("""
        ALTER TABLE users
            ADD CONSTRAINT users_tenant_id_fkey
            FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE;
    """)


def down():
    if DB.dialect.supports("rls"):
        Schema.raw("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_tenant_id_fkey;")
    Schema.drop_column("users", "tenant_id")
