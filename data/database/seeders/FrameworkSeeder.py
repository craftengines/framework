"""Framework tables seeder — populates translations, modules, roles, and permissions."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.seeding import Seeder
from craft.facades import DB
from database.seeders.TranslationSeeder import TranslationSeeder
from app.Models.Module import Module
from app.Models.Role import Role
from app.Models.Permission import Permission


class FrameworkSeeder(Seeder):
    def run(self):
        # 1. Clean tables
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
