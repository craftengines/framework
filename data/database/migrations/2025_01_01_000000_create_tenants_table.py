"""Migration: the tenants table every tenant-scoped table points at.

Runs first, before anything else. `t.tenant_scoped()` adds a `tenant_id`
referencing `tenants (id)` by default, so without this table that call fails
outright on PostgreSQL — `relation "tenants" does not exist` — and the feature
the framework advertises as "the whole tenancy contract in one line" cannot be
used out of the box.

The table exists whether or not multi-tenancy is enabled. It costs nothing
empty, and its absence is what turns turning tenancy on from a config change
into a schema migration.

Category: Framework schema (multi-tenancy).
References:
  - Guide: `documentation/postgres.md#multi-tenancy`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.facades import Schema


def up():
    Schema.create_table("tenants", lambda t: (
        # A UUID key, not a sequence: a tenant id travels in URLs, in the
        # `app.current_tenant_id` session variable and in every job payload,
        # and a sequential integer there leaks how many customers exist.
        # `Model.key_type = "uuid"` fills it with a time-ordered v7.
        t.uuid_primary(),
        t.string("name"),
        # The subdomain `ScopeTenant` resolves against. Unique because two
        # tenants answering to one host is not a conflict to resolve at
        # request time — it is a provisioning mistake.
        t.string("slug", 64).unique(),
        t.boolean("is_active").default(True),
        t.timestamps(),
        t.soft_deletes(),
    ))


def down():
    Schema.drop_table("tenants")
