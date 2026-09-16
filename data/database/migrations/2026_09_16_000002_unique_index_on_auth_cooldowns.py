"""Migration: a unique index `auth_cooldowns` needs for an atomic upsert.

`HoneypotService.record_attempt()` used to read the current failed-attempt
count, add one, then write it back in a separate statement — a classic
TOCTOU race: two concurrent failed logins (exactly what an automated
brute-force tool produces) could both read the same count and both write
`count + 1`, silently losing an increment and letting the attacker try more
times than the limit allows. Fixing it means an atomic
`INSERT ... ON CONFLICT ... DO UPDATE`, which needs a unique constraint on
the columns being conflicted on.

Category: Framework schema (auth security).
References:
  - Plan: `.claude/plans/softpax-upstream-roadmap.md` (Slice 0 item 0.11,
    Slice 2 "sliding-window login limiter with atomic upsert")
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.facades import DB, Schema


def up():
    # A unique index creation fails outright if a duplicate pair already
    # exists from before this constraint existed - keep the most recently
    # updated row per (identifier_type, identifier_value) and drop the rest,
    # rather than let the migration fail on an installation with live data.
    DB.statement("""
        DELETE FROM auth_cooldowns
        WHERE id NOT IN (
            SELECT MAX(id) FROM auth_cooldowns
            GROUP BY identifier_type, identifier_value
        )
    """)
    Schema.table("auth_cooldowns", lambda t: (
        t.unique_index(["identifier_type", "identifier_value"], name="uq_auth_cooldowns_identifier"),
    ))


def down():
    DB.statement('DROP INDEX IF EXISTS "uq_auth_cooldowns_identifier"')
