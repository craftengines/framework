"""Create media table for database-backed multimedia tracking."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.migrations import Schema


def up():
    Schema.create_table("media", lambda t: (
        t.id(type="integer"),
        t.string("model_type").nullable(),
        t.big_integer("model_id").nullable(),
        t.string("collection_name").default("default"),
        t.string("disk").default("public"),
        t.string("filename"),
        t.string("mime_type"),
        t.big_integer("size").default(0),
        t.integer("width").nullable(),
        t.integer("height").nullable(),
        t.text("conversions").nullable(),  # JSON encoded thumbnails/variants
        t.timestamps(),
    ))


def down():
    Schema.drop_table("media")
