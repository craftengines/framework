"""Auth service provider — register policies and gates."""

from codepy.providers import ServiceProvider
from codepy.facades import Gate


class AuthServiceProvider(ServiceProvider):
    def register(self):
        pass

    def boot(self):
        from app.Models.Post import Post
        from app.Policies.PostPolicy import PostPolicy
        Gate.policy(Post, PostPolicy)

        Gate.define("is-admin", lambda user: user is not None and user.get_attribute("is_admin"))
