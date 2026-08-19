"""Auth controller — login, register, logout under Auth directory."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.http.controller import Controller
from craft.http.response import redirect
from craft.facades import Auth, Captcha
from app.Models.User import User


class AuthController(Controller):
    def show_login(self, request):
        code = Captcha.generate(request)
        obfuscated_html = Captcha.get_obfuscated_html(code)
        return self.view("auth.login", {"captcha_html": obfuscated_html})

    def login(self, request):
        captcha_input = request.get_input("captcha")
        if not Captcha.validate(request, captcha_input):
            code = Captcha.generate(request)
            obfuscated_html = Captcha.get_obfuscated_html(code)
            return self.view("auth.login", {
                "error": "Security check: Invalid CAPTCHA code.",
                "captcha_html": obfuscated_html
            })

        credentials = {
            "email": request.get_input("email"),
            "password": request.get_input("password"),
        }
        if Auth.attempt(credentials):
            return redirect(route="home")

        code = Captcha.generate(request)
        obfuscated_html = Captcha.get_obfuscated_html(code)
        return self.view("auth.login", {
            "error": "Invalid credentials",
            "captcha_html": obfuscated_html
        })

    def show_register(self, request):
        return self.view("auth.register", {})

    def register(self, request):
        name = (request.get_input("name") or "").strip()
        email = (request.get_input("email") or "").strip()
        password = request.get_input("password") or ""

        from app.Services.Identity.DomainValidator import DomainValidator
        if not DomainValidator.is_allowed_email(email, allow_system_domains=True):
            return self.view("auth.register", {
                "error": "Email domain is not authorized for registration.",
                "old": {"name": name, "email": email}
            })

        user = User.create({
            "name": name,
            "email": email,
            "password": password,
        })
        Auth.login(user)
        return redirect(route="home")

    def logout(self, request):
        Auth.logout()
        return redirect(route="home")
