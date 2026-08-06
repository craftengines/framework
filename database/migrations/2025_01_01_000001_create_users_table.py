"""Create users table."""

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
