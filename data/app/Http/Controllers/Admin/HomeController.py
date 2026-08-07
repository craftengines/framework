"""Home Controller for Admin and Dashboard views."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.http.controller import Controller
from craft.http.response import redirect


class HomeController(Controller):
    def index(self, request):
        # Fetch recent posts for the landing page community section
        try:
            from app.Models.Post import Post
            posts = Post.query().order_by("created_at", "desc").limit(6).get()
        except Exception:
            posts = []
        return self.view("home", {"posts": posts, "show_sidebar": False})

    def admin(self, request):
        from craft.facades import Auth
        user = Auth.user()
        if not user:
            return redirect(url="/login", status=302)

        from app.Models.User import User
        from app.Services.Tenant.TenantService import TenantService

        try:
            tenants = TenantService().get_active_tenants()
        except Exception:
            tenants = []

        try:
            users = User.query().order_by("created_at", "desc").get()
        except Exception:
            users = []

        try:
            administrators = User.query().where("is_admin", True).get()
        except Exception:
            administrators = []

        return self.view("admin.dashboard", {
            "tenants": tenants,
            "administrators": administrators,
            "users": users,
            "show_sidebar": True,
        })

