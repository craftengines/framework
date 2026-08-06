"""Create system_logs table."""
# Codepy Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from codepy.migrations import Migration, Schema


def up():
    Schema.create_table("system_logs", lambda t: (
        t.id(type="integer"),
        t.string("level"),
        t.text("message"),
        t.text("context").nullable(),
        t.timestamps(),
    ))


def down():
    Schema.drop_table("system_logs")
