"""Authenticate middleware — redirects unauthenticated users."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.http.middleware import Middleware
from craft.facades import Auth
from craft.http.response import redirect


class Authenticate(Middleware):
    def handle(self, request, next):
        if not Auth.check():
            if request.expects_json():
                from craft.http.response import JsonResponse
                return JsonResponse({"message": "Unauthenticated."}, status=401)
            return redirect(route="login")
        return next(request)
