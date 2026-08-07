"""User Model for Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from typing import Any, Dict

from services.auth.password import Hash
from services.orm.model import Model


class User(Model):
    __table__ = "users"

    # `is_admin` and `type` gate authorization (PostPolicy, TenantMiddleware)
    # and must never be settable via mass assignment from request input —
    # only through a trusted, explicit path (e.g. Model.force_create /
    # direct set_attribute in an admin-only action).
    fillable = ["name", "email", "password"]
    hidden = ["password", "remember_token"]

    @classmethod
    def create(cls, attributes: Dict[str, Any]) -> "User":
        """Hash the password on the way in — never store plaintext."""
        attributes = dict(attributes)
        password = attributes.get("password")
        if password and not Hash.is_hashed(password):
            attributes["password"] = Hash.make(password)
        return super().create(attributes)

    def check_password(self, password: str) -> bool:
        return Hash.check(password, self.get_attribute("password"))

    def posts(self):
        from app.Models.Post import Post

        return self.has_many(Post, foreign_key="user_id")
