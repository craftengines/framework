"""AuthCooldown Model for Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.orm.model import Model


class AuthCooldown(Model):
    __table__ = "auth_cooldowns"

    fillable = [
        "identifier_type",
        "identifier_value",
        "failed_attempts",
        "blocked_until",
    ]
