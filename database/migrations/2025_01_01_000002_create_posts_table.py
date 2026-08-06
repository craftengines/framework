"""Create posts table."""

from codepy.migrations import Migration, Schema


def up():
    Schema.create_table("posts", lambda t: (
        t.id(),
        t.foreign_id("user_id").constrained().cascade_on_delete(),
        t.string("title"),
        t.text("body"),
        t.boolean("published").default(False),
        t.datetime("published_at").nullable(),
        t.timestamps(),
    ))


def down():
    Schema.drop_table("posts")
