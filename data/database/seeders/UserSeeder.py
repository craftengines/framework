"""User seeder."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.seeding import Seeder
from app.Models.User import User


class UserSeeder(Seeder):
    def run(self):
        User.create({
            "name": "Standard User",
            "email": "user@craft.local",
            "password": "craft",
            "type": "user",
            "is_admin": False,
        })
        User.create({
            "name": "Tenant User",
            "email": "tenant@craft.local",
            "password": "craft",
            "type": "tenant",
            "is_admin": False,
        })
        User.create({
            "name": "Admin User",
            "email": "admin@craft.local",
            "password": "craft",
            "type": "admin",
            "is_admin": True,
        })
