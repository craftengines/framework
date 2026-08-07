"""Auth service provider — register policies and gates."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.providers import ServiceProvider
from craft.facades import Gate


class AuthServiceProvider(ServiceProvider):
    def register(self):
        pass

    def boot(self):
        from app.Models.Post import Post
        from app.Policies.PostPolicy import PostPolicy
        Gate.policy(Post, PostPolicy)

        Gate.define("is-admin", lambda user: user is not None and user.get_attribute("is_admin"))
