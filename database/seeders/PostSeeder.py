"""Post seeder."""
# Codepy Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from codepy.seeding import Seeder
from app.Models.Post import Post


class PostSeeder(Seeder):
    def run(self):
        from app.Models.User import User
        admin = User.query().where("email", "admin@codepy.local").first()
        jane = User.query().where("email", "user@codepy.local").first()

        admin_id = admin.get_attribute("id") if admin else None
        jane_id = jane.get_attribute("id") if jane else None

        Post.create({
            "title": "Welcome to Codepy",
            "body": "Codepy is a Python FastAPI framework inspired by Codepy. This is the first post!",
            "user_id": admin_id,
            "published": True,
        })
        Post.create({
            "title": "Getting Started with Codepyquent",
            "body": "The Codepyquent ORM provides an Eloquent-like active record experience in Python.",
            "user_id": admin_id,
            "published": True,
        })
        Post.create({
            "title": "Building APIs with Codepy",
            "body": "Codepy makes it easy to build JSON APIs with FormRequests and API Resources.",
            "user_id": jane_id,
            "published": False,
        })
