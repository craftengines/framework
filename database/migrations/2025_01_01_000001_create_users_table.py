"""Create users table."""
# Codepy Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from codepy.migrations import Migration, Schema


def up():
    Schema.create_table("users", lambda t: (
        t.id(),
        t.string("name"),
        t.string("email").unique(),
        t.string("password"),
        t.boolean("is_admin").default(False),
        t.string("type").default("user"),
        t.datetime("email_verified_at").nullable(),
        t.string("remember_token", 100).nullable(),
        t.timestamps(),
    ))


def down():
    Schema.drop_table("users")
