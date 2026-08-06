"""Authenticate middleware — redirects unauthenticated users."""
# Codepy Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from codepy.http.middleware import Middleware
from codepy.facades import Auth
from codepy.http.response import redirect


class Authenticate(Middleware):
    def handle(self, request, next):
        if not Auth.check():
            if request.expects_json():
                from codepy.http.response import JsonResponse
                return JsonResponse({"message": "Unauthenticated."}, status=401)
            return redirect(route="login")
        return next(request)
