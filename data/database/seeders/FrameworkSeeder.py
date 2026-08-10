"""Framework tables seeder — translations, modules, and the whole authorization
starter set: roles, permissions, groups and one conditional (ABAC) grant.

A fresh installation comes up with a working three-tier ladder rather than an
empty `roles` table, so the admin UI, the route middleware and the demo
accounts are all exercisable the minute `migrate --seed` finishes. See
`documentation/authorization.md`.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.auth.conditions import dump
from craft.seeding import Seeder
from craft.facades import DB
from database.seeders.TranslationSeeder import TranslationSeeder
from app.Models.Group import Group
from app.Models.Module import Module
from app.Models.Role import Role
from app.Models.Permission import Permission


class FrameworkSeeder(Seeder):
    def run(self):
        # 1. Clean tables. Order matters: the pivots reference the rows below
        # them, so they go first.
        DB.statement("DELETE FROM permission_user")
        DB.statement("DELETE FROM permission_group")
        DB.statement("DELETE FROM group_role")
        DB.statement("DELETE FROM group_user")
        DB.statement("DELETE FROM groups")
        DB.statement("DELETE FROM permission_role")
        DB.statement("DELETE FROM role_user")
        DB.statement("DELETE FROM permissions")
        DB.statement("DELETE FROM roles")
        DB.statement("DELETE FROM modules")

        # 2. Seed translations (all locales live in TranslationSeeder)
        self.call(TranslationSeeder)

        # 3. Seed modules
        Module.create({"name": "Inventory Management", "slug": "inventory", "enabled": True})
        Module.create({"name": "Billing Services", "slug": "billing", "enabled": True})

        # 4. Seed Roles
        # A 3-tier ladder matches the 3 seeded demo users: `user` (basic) ->
        # `tenant-manager` (elevated, can manage users but isn't a full admin)
        # -> `admin` (full access).
        admin_role = Role.create({"name": "Administrator", "slug": "admin"})
        user_role = Role.create({"name": "User", "slug": "user"})
        tenant_manager_role = Role.create({"name": "Tenant Manager", "slug": "tenant-manager"})

        # 5. Seed Permissions
        create_post = Permission.create({"name": "Create Posts", "slug": "create-post"})
        delete_post = Permission.create({"name": "Delete Posts", "slug": "delete-post"})
        manage_users = Permission.create({"name": "Manage Users", "slug": "manage-users"})

        # 6. Populate Pivot Tables (permission_role)
        # admin gets all permissions
        DB.statement(
            "INSERT INTO permission_role (role_id, permission_id) VALUES (:role, :perm)",
            {"role": admin_role.get_attribute("id"), "perm": create_post.get_attribute("id")}
        )
        DB.statement(
            "INSERT INTO permission_role (role_id, permission_id) VALUES (:role, :perm)",
            {"role": admin_role.get_attribute("id"), "perm": delete_post.get_attribute("id")}
        )
        DB.statement(
            "INSERT INTO permission_role (role_id, permission_id) VALUES (:role, :perm)",
            {"role": admin_role.get_attribute("id"), "perm": manage_users.get_attribute("id")}
        )

        # user gets create and delete posts
        DB.statement(
            "INSERT INTO permission_role (role_id, permission_id) VALUES (:role, :perm)",
            {"role": user_role.get_attribute("id"), "perm": create_post.get_attribute("id")}
        )
        DB.statement(
            "INSERT INTO permission_role (role_id, permission_id) VALUES (:role, :perm)",
            {"role": user_role.get_attribute("id"), "perm": delete_post.get_attribute("id")}
        )

        # tenant-manager gets everything user has, plus manage-users — elevated
        # but short of full admin.
        DB.statement(
            "INSERT INTO permission_role (role_id, permission_id) VALUES (:role, :perm)",
            {"role": tenant_manager_role.get_attribute("id"), "perm": create_post.get_attribute("id")}
        )
        DB.statement(
            "INSERT INTO permission_role (role_id, permission_id) VALUES (:role, :perm)",
            {"role": tenant_manager_role.get_attribute("id"), "perm": delete_post.get_attribute("id")}
        )
        DB.statement(
            "INSERT INTO permission_role (role_id, permission_id) VALUES (:role, :perm)",
            {"role": tenant_manager_role.get_attribute("id"), "perm": manage_users.get_attribute("id")}
        )

        # 7. Associate Users to Roles (role_user)
        from app.Models.User import User
        admin_user = User.query().where("email", "admin@craft.local").first()
        jane_user = User.query().where("email", "user@craft.local").first()
        tenant_user = User.query().where("email", "tenant@craft.local").first()

        if admin_user:
            DB.statement(
                "INSERT INTO role_user (user_id, role_id) VALUES (:user, :role)",
                {"user": admin_user.get_attribute("id"), "role": admin_role.get_attribute("id")}
            )
        if jane_user:
            DB.statement(
                "INSERT INTO role_user (user_id, role_id) VALUES (:user, :role)",
                {"user": jane_user.get_attribute("id"), "role": user_role.get_attribute("id")}
            )
        if tenant_user:
            DB.statement(
                "INSERT INTO role_user (user_id, role_id) VALUES (:user, :role)",
                {"user": tenant_user.get_attribute("id"), "role": tenant_manager_role.get_attribute("id")}
            )

        # 8. Groups — access granted to a team instead of one person at a time.
        # `content-team` grants the `user` role to every member, so adding
        # someone to the team is one row rather than a tour of the roles they
        # need. The standard demo account is a member, which makes the group
        # path exercisable straight after `migrate --seed`.
        content_team = Group.create({
            "name": "Content Team",
            "slug": "content-team",
            "description": "Writers and editors. Members inherit the `user` role.",
        })
        DB.statement(
            "INSERT INTO group_role (group_id, role_id) VALUES (:group, :role)",
            {"group": content_team.get_attribute("id"), "role": user_role.get_attribute("id")},
        )
        if jane_user:
            DB.statement(
                "INSERT INTO group_user (user_id, group_id) VALUES (:user, :group)",
                {"user": jane_user.get_attribute("id"), "group": content_team.get_attribute("id")},
            )

        # 9. One conditional grant (ABAC), so the feature is visible rather than
        # merely documented: the Content Team may publish, but only their own
        # drafts. `@user.id` is replaced with the acting user's id at check
        # time, and the condition is evaluated against the record being acted
        # upon — see `craft.auth.conditions`.
        publish_post = Permission.create({"name": "Publish Posts", "slug": "publish-post"})
        DB.statement(
            "INSERT INTO permission_group (group_id, permission_id, conditions) "
            "VALUES (:group, :perm, :conditions)",
            {
                "group": content_team.get_attribute("id"),
                "perm": publish_post.get_attribute("id"),
                "conditions": dump({"user_id": "@user.id"}),
            },
        )
        # Administrators publish anything: the same permission, unconditional.
        DB.statement(
            "INSERT INTO permission_role (role_id, permission_id) VALUES (:role, :perm)",
            {"role": admin_role.get_attribute("id"), "perm": publish_post.get_attribute("id")},
        )
