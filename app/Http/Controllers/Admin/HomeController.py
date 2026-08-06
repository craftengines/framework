"""Home Controller for Admin and Dashboard views."""
# Codepy Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from codepy.http.controller import Controller
from codepy.http.response import Response, redirect


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
        from codepy.facades import Auth
        user = Auth.user()
        if not user:
            return redirect(url="/login", status=302)
        return Response("<h1>Admin Dashboard</h1>")

