"""Create jobs table for queue."""

from codepy.migrations import Migration, Schema


def up():
    Schema.create_table("jobs", lambda t: (
        t.id(type="integer"),
        t.string("queue").default("default"),
        t.text("payload"),
        t.integer("attempts").default(0),
        # Timestamps are stored as ISO-8601 strings by the queue manager, so
        # these must be datetime columns — integers break on PostgreSQL.
        t.datetime("reserved_at").nullable(),
        t.datetime("available_at").nullable(),
        t.datetime("created_at").nullable(),
    ))


def down():
    Schema.drop_table("jobs")
