"""Create the plugins table (disk-discovered, DB-persisted plugin registry)."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.migrations import Migration, Schema


def up():
    Schema.create_table("plugins", lambda t: (
        t.id(),
        t.string("name"),
        t.string("slug").unique(),
        t.boolean("enabled").default(True),
        t.string("path").nullable(),
        t.timestamps(),
    ))


def down():
    Schema.drop_table("plugins")
