"""User factory."""

from codepy.factories import Factory
from faker import Faker


class UserFactory(Factory):
    model = None  # Set to User model at runtime

    def definition(self):
        f = Faker()
        return {
            "name": f.name(),
            "email": f.unique().email(),
            "password": "password",
        }

    def unverified(self):
        return {"email_verified_at": None}

    def admin(self):
        return {"is_admin": True}
