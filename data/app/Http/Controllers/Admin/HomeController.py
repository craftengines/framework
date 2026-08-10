"""Home Controller for Admin and Dashboard views."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.http.controller import Controller
from craft.http.response import redirect


class HomeController(Controller):
    def index(self, request):
        """The public landing page.

        The recent-posts strip is decorative, so a query failure degrades to an
        empty list rather than a 500 on the site's front door — but it is
        logged, because "the community section is empty" and "the database is
        unreachable" look identical to a visitor.
        """
        import logging

        from app.Models.Post import Post

        try:
            posts = Post.query().order_by("created_at", "desc").limit(6).get()
        except Exception:
            logging.getLogger("craft").warning(
                "Could not load recent posts for the landing page; rendering "
                "the section empty.", exc_info=True,
            )
            posts = []

        return self.view("home", {"posts": posts, "show_sidebar": False})

    def admin(self, request):
        from craft.facades import Auth
        user = Auth.user()
        if not user:
            return redirect(url="/login", status=302)

        import logging

        from app.Models.User import User
        from app.Services.Tenant.TenantService import TenantService

        # The user and admin counts are the dashboard's actual content. They
        # used to be wrapped in `except: []` each, so an unreachable database
        # rendered a healthy-looking dashboard reporting zero of everything —
        # the worst possible answer, because it is indistinguishable from a
        # correct one. Let it fail and reach the exception handler.
        users = User.query().order_by("created_at", "desc").get()
        administrators = User.query().where("is_admin", True).get()

        # Tenancy is optional and may not be provisioned at all, so an empty
        # list is a legitimate result here rather than a swallowed failure.
        try:
            tenants = TenantService().get_active_tenants()
        except Exception:
            logging.getLogger("craft").info(
                "No tenant list available for the dashboard.", exc_info=True
            )
            tenants = []

        return self.view("admin.dashboard", {
            "tenants": tenants,
            "administrators": administrators,
            "users": users,
            "show_sidebar": True,
        })

