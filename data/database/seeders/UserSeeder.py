"""User seeder."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.seeding import Seeder
from app.Models.User import User


class UserSeeder(Seeder):
    """Seeds the framework's 3 official demo accounts.

    Uses `force_create` deliberately: `type` and `is_admin` are excluded from
    `User.fillable` so request input can never escalate privileges, which
    means `create()` would silently drop them and seed three identical
    non-admin accounts. Seeding is a trusted path, so it bypasses the guard.
    """

    def run(self):
        User.force_create({
            "name": "Standard User",
            "email": "user@craft.local",
            "password": "craft",
            "type": "user",
            "is_admin": False,
        })
        User.force_create({
            "name": "Tenant User",
            "email": "tenant@craft.local",
            "password": "craft",
            "type": "tenant",
            "is_admin": False,
        })
        User.force_create({
            "name": "Admin User",
            "email": "admin@craft.local",
            "password": "craft",
            "type": "admin",
            "is_admin": True,
        })
