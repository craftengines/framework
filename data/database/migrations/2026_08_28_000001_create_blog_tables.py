"""Create blog domain tables: blog_categories, blog_posts, blog_tags, blog_post_tag, blog_comments."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.migrations import Schema


def up():
    Schema.create_table("blog_categories", lambda t: (
        t.id(),
        t.string("name"),
        t.string("slug").unique(),
        t.text("description").nullable(),
        t.timestamps(),
    ))

    Schema.create_table("blog_posts", lambda t: (
        t.id(),
        t.uuid().nullable(),
        t.integer("user_id").nullable(),
        t.integer("category_id").nullable(),
        t.string("title"),
        t.string("slug").unique(),
        t.text("excerpt").nullable(),
        t.text("content"),
        t.string("status").default("draft"),
        t.datetime("published_at").nullable(),
        t.timestamps(),
    ))

    Schema.create_table("blog_tags", lambda t: (
        t.id(),
        t.string("name"),
        t.string("slug").unique(),
        t.timestamps(),
    ))

    Schema.create_table("blog_post_tag", lambda t: (
        t.id(),
        t.integer("post_id"),
        t.integer("tag_id"),
    ))

    Schema.create_table("blog_comments", lambda t: (
        t.id(),
        t.integer("post_id"),
        t.string("author_name"),
        t.string("author_email"),
        t.text("content"),
        t.string("status").default("approved"),
        t.timestamps(),
    ))


def down():
    Schema.drop_table("blog_comments")
    Schema.drop_table("blog_post_tag")
    Schema.drop_table("blog_tags")
    Schema.drop_table("blog_posts")
    Schema.drop_table("blog_categories")
