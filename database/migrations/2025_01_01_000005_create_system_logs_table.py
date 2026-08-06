"""Create system_logs table."""

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
