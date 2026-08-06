"""Auth controller — login, register, logout under Auth directory."""
# Codepy Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from codepy.http.controller import Controller
from codepy.http.response import redirect
from codepy.facades import Auth, Captcha
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
        user = User.create({
            "name": request.get_input("name"),
            "email": request.get_input("email"),
            "password": request.get_input("password"),
        })
        Auth.login(user)
        return redirect(route="home")

    def logout(self, request):
        Auth.logout()
        return redirect(route="home")
