"""Migration: distinguish a suspended tenant from one that never existed.

`is_active` is a boolean, so `ScopeTenant.resolve()` cannot tell "this
subdomain names no tenant" (404 — a stranger, tell them nothing) from "this
subdomain names a suspended tenant" (403 — a real customer, tell them why)
without a third state. `status` carries that distinction; `is_active` is kept
and backfilled from it so anything still reading the boolean column keeps
working (NR-05) until a later release contracts it away.

Category: Framework schema (multi-tenancy).
References:
  - Plan: `.claude/plans/slice-1-data-integrity-and-tenant-isolation.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.facades import DB, Schema

ACTIVE = "active"
SUSPENDED = "suspended"


def up():
    Schema.table("tenants", lambda t: (
        t.string("status", 32).default(ACTIVE),
    ))
    # Backfill from the existing boolean so a tenant already marked inactive
    # reads as suspended rather than silently "active" under the new column.
    DB.statement("UPDATE tenants SET status = ? WHERE is_active = ?", [SUSPENDED, False])


def down():
    Schema.drop_column("tenants", "status")
