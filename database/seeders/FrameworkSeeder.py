"""Framework tables seeder — populates translations, modules, roles, and permissions."""
# Codepy Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from codepy.seeding import Seeder
from codepy.facades import DB
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
        admin_role = Role.create({"name": "Administrator", "slug": "admin"})
        user_role = Role.create({"name": "User", "slug": "user"})

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

        # 7. Associate Users to Roles (role_user)
        from app.Models.User import User
        admin_user = User.query().where("email", "admin@codepy.local").first()
        jane_user = User.query().where("email", "user@codepy.local").first()

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
