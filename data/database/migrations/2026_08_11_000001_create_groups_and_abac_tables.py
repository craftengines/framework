"""Groups, direct user grants, and attribute conditions on every grant.

Before this migration, authorization could only say *who you are*: a user held
roles, and roles held permissions. Two things were missing for real systems.

**Groups.** Organisations grant access to a team, a department or a tenant unit
— not to one person at a time. A group collects users and carries roles and/or
permissions of its own, so onboarding someone is one insert rather than a tour
of every role they need.

**Conditions (ABAC).** A permission is often not absolute: *edit articles, but
only your own*; *approve invoices, but only under 10k*; *read patients, but only
in your own department*. Those are attributes of the resource and of the user,
not of the role. Every grant table therefore carries a nullable `conditions`
column holding a small JSON object, evaluated against the resource at check
time. `NULL` means unconditional, which is exactly the old behaviour — existing
grants keep working untouched.

Four ways a permission can reach a user, all resolved together:

    user → permission                     (permission_user, direct)
    user → role → permission              (role_user + permission_role)
    user → group → role → permission      (group_user + group_role + permission_role)
    user → group → permission             (group_user + permission_group)
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.migrations import Migration, Schema  # noqa: F401  (Migration re-exported for symmetry)


def up():
    # -- Groups ---------------------------------------------------------------
    Schema.create_table("groups", lambda t: (
        t.id(),
        t.string("name").unique(),
        t.string("slug").unique(),
        t.text("description").nullable(),
        t.timestamps(),
    ))

    # Membership. Pivot keys are big integers to match the auto-incrementing
    # primary keys they join against, the same choice `role_user` makes.
    Schema.create_table("group_user", lambda t: (
        t.id(type="integer"),
        t.big_integer("user_id"),
        t.big_integer("group_id"),
        t.timestamps(),
        t.index_on(["user_id"]),
        t.unique_index(["user_id", "group_id"], name="group_user_unique"),
    ))

    # A group grants roles — the common case: "the support team are agents".
    Schema.create_table("group_role", lambda t: (
        t.id(type="integer"),
        t.big_integer("group_id"),
        t.big_integer("role_id"),
        #: JSON object, NULL when the grant is unconditional. See
        #: `engine/auth/conditions.py` for the accepted shape.
        t.text("conditions").nullable(),
        t.timestamps(),
        t.unique_index(["group_id", "role_id"], name="group_role_unique"),
    ))

    # A group can also grant a single permission without inventing a role for it.
    Schema.create_table("permission_group", lambda t: (
        t.id(type="integer"),
        t.big_integer("permission_id"),
        t.big_integer("group_id"),
        t.text("conditions").nullable(),
        t.timestamps(),
        t.unique_index(["permission_id", "group_id"], name="permission_group_unique"),
    ))

    # -- Direct grants to one user -------------------------------------------
    # The exception that every real system needs eventually: one person gets one
    # extra permission, and inventing a single-member role for it is worse than
    # recording it honestly.
    Schema.create_table("permission_user", lambda t: (
        t.id(type="integer"),
        t.big_integer("permission_id"),
        t.big_integer("user_id"),
        t.text("conditions").nullable(),
        t.timestamps(),
        t.unique_index(["permission_id", "user_id"], name="permission_user_unique"),
    ))

    # -- Conditions on the pre-existing grant tables --------------------------
    # Added rather than recreated, so installations keep their data.
    Schema.table("permission_role", lambda t: (
        t.text("conditions").nullable(),
    ))
    Schema.table("role_user", lambda t: (
        t.text("conditions").nullable(),
    ))


def down():
    Schema.drop_column("role_user", "conditions")
    Schema.drop_column("permission_role", "conditions")
    Schema.drop_table("permission_user")
    Schema.drop_table("permission_group")
    Schema.drop_table("group_role")
    Schema.drop_table("group_user")
    Schema.drop_table("groups")
