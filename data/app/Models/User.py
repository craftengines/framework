"""User Model for Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from typing import Any, Dict

from craft.auth.password import Hash
from craft.orm.model import Model


class User(Model):
    __table__ = "users"

    # `is_admin` and `type` gate authorization (PostPolicy, TenantMiddleware)
    # and must never be settable via mass assignment from request input —
    # only through a trusted, explicit path (e.g. Model.force_create /
    # direct set_attribute in an admin-only action).
    fillable = ["name", "email", "password"]
    hidden = ["password", "remember_token"]

    @classmethod
    def force_create(cls, attributes: Dict[str, Any]) -> "User":
        """Hash the password on the way in — never store plaintext.

        Hooked on `force_create` rather than `create` so that *every* insert
        path hashes: `create()` funnels through here after mass-assignment
        filtering, and trusted callers that bypass the guard (seeders, admin
        actions setting `type`/`is_admin`) get the same guarantee.
        """
        attributes = dict(attributes)
        password = attributes.get("password")
        if password and not Hash.is_hashed(password):
            attributes["password"] = Hash.make(password)
        return super().force_create(attributes)

    def check_password(self, password: str) -> bool:
        return Hash.check(password, self.get_attribute("password"))

    def posts(self):
        from app.Models.Post import Post

        return self.has_many(Post, foreign_key="user_id")

    # -- RBAC ------------------------------------------------------------
    # These used to sit on the framework's base `Model`, so every model in the
    # application answered `roles()` with the roles of the *user* holding the
    # same id. They belong to the model they actually describe.

    def roles(self):
        """Roles assigned to this user, through the `role_user` pivot."""
        from craft.orm.relationships import BelongsToMany
        from app.Models.Role import Role

        return BelongsToMany(
            self,
            Role,
            pivot_table="role_user",
            foreign_pivot_key="user_id",
            related_pivot_key="role_id",
            name="roles",
        )

    def has_role(self, slug: str) -> bool:
        from craft.facades import DB

        rows = DB.statement(
            """
            SELECT r.slug FROM roles r
            JOIN role_user ru ON r.id = ru.role_id
            WHERE ru.user_id = ? AND r.slug = ?
            """,
            [self.get_attribute("id"), slug],
            read=True,
        ).fetchall()
        return len(rows) > 0

    def has_permission(self, slug: str) -> bool:
        """Whether any of this user's roles grants the permission."""
        from craft.facades import DB

        rows = DB.statement(
            """
            SELECT p.slug FROM permissions p
            JOIN permission_role pr ON p.id = pr.permission_id
            JOIN role_user ru ON pr.role_id = ru.role_id
            WHERE ru.user_id = ? AND p.slug = ?
            """,
            [self.get_attribute("id"), slug],
            read=True,
        ).fetchall()
        return len(rows) > 0
