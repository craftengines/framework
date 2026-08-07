"""Create framework dynamic tables (translations, modules, settings and RBAC)."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.migrations import Migration, Schema


def up():
    # 1. Translations table
    Schema.create_table("translations", lambda t: (
        t.id(),
        t.string("key"),
        t.string("locale"),
        t.text("value"),
        t.timestamps(),
    ))

    # 2. Modules table
    Schema.create_table("modules", lambda t: (
        t.id(),
        t.string("name"),
        t.string("slug").unique(),
        t.boolean("enabled").default(True),
        t.timestamps(),
    ))

    # 3. Roles table
    Schema.create_table("roles", lambda t: (
        t.id(),
        t.string("name").unique(),
        t.string("slug").unique(),
        t.text("description").nullable(),
        t.timestamps(),
    ))

    # 4. Permissions table
    Schema.create_table("permissions", lambda t: (
        t.id(),
        t.string("name").unique(),
        t.string("slug").unique(),
        t.timestamps(),
    ))

    # 5. Role-User pivot. Keys are big integers to match the auto-incrementing
    # primary keys on `users` and `roles` — they were UUID columns before, which
    # never joined against anything.
    Schema.create_table("role_user", lambda t: (
        t.id(type="integer"),
        t.big_integer("user_id"),
        t.big_integer("role_id"),
        t.timestamps(),
    ))

    # 6. Permission-Role pivot — required by Model.has_permission(); it was
    # dropped in down() but never created here.
    Schema.create_table("permission_role", lambda t: (
        t.id(type="integer"),
        t.big_integer("permission_id"),
        t.big_integer("role_id"),
        t.timestamps(),
    ))

    # 7. Settings table
    Schema.create_table("settings", lambda t: (
        t.id(type="integer"),
        t.string("key").unique(),
        t.text("value"),
        t.timestamps(),
    ))


def down():
    Schema.drop_table("settings")
    Schema.drop_table("permission_role")
    Schema.drop_table("role_user")
    Schema.drop_table("permissions")
    Schema.drop_table("roles")
    Schema.drop_table("modules")
    Schema.drop_table("translations")
