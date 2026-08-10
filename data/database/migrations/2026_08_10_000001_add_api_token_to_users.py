"""Give the `api` auth guard the column it has always referenced.

`config/auth.py` declares `guards.api.token_name = "api_token"` and
`AuthenticateApiToken` queries that column, but no migration ever created it —
so bearer-token authentication could not succeed for anyone. The guard was a
promise with no schema behind it.

Nullable: most accounts never use the API, and a token is issued deliberately.
Uniqueness comes from the index rather than an inline constraint, because
SQLite rejects UNIQUE on ALTER TABLE ADD COLUMN.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.facades import DB
from craft.migrations import Migration, Schema


def up():
    Schema.table("users", lambda t: t.string("api_token", 80).nullable())

    # A partial index would be tidier, but it is not portable across the three
    # supported drivers. A plain unique index still permits many NULLs on
    # SQLite, PostgreSQL and MySQL, which is the behaviour that matters here.
    DB.statement(
        'CREATE UNIQUE INDEX IF NOT EXISTS "uniq_users_api_token" '
        'ON "users" ("api_token")'
    )


def down():
    DB.statement('DROP INDEX IF EXISTS "uniq_users_api_token"')
    Schema.drop_column("users", "api_token")
