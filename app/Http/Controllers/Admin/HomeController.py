"""Home Controller for Admin and Dashboard views."""
# Codepy Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from codepy.http.controller import Controller
from codepy.http.response import Response, redirect


class HomeController(Controller):
    def index(self, request):
        return Response("<h1>Recent Posts</h1><p>Welcome to Codepy Application</p>")

    def admin(self, request):
        from codepy.facades import Auth
        user = Auth.user()
        if not user:
            return redirect(url="/login", status=302)
        return Response("<h1>Admin Dashboard</h1>")
