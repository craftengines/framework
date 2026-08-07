"""Post seeder."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.seeding import Seeder
from app.Models.Post import Post


class PostSeeder(Seeder):
    def run(self):
        from app.Models.User import User
        admin = User.query().where("email", "admin@craft.local").first()
        jane = User.query().where("email", "user@craft.local").first()

        admin_id = admin.get_attribute("id") if admin else None
        jane_id = jane.get_attribute("id") if jane else None

        Post.create({
            "title": "Welcome to Craft",
            "body": "Craft is a Python web framework built on Starlette. This is the first post!",
            "user_id": admin_id,
            "published": True,
        })
        Post.create({
            "title": "Getting Started with Craft ORM",
            "body": "The Craft ORM provides a fluent active record experience in Python.",
            "user_id": admin_id,
            "published": True,
        })
        Post.create({
            "title": "Building APIs with Craft",
            "body": "Craft makes it easy to build JSON APIs with FormRequests and API Resources.",
            "user_id": jane_id,
            "published": False,
        })
