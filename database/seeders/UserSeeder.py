"""User seeder."""

from codepy.seeding import Seeder
from app.Models.User import User


class UserSeeder(Seeder):
    def run(self):
        User.create({
            "name": "Standard User",
            "email": "user@codepy.local",
            "password": "codepy",
            "type": "user",
            "is_admin": False,
        })
        User.create({
            "name": "Tenant User",
            "email": "tenant@codepy.local",
            "password": "codepy",
            "type": "tenant",
            "is_admin": False,
        })
        User.create({
            "name": "Admin User",
            "email": "admin@codepy.local",
            "password": "codepy",
            "type": "admin",
            "is_admin": True,
        })
