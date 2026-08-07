"""Web routes for Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.facades import Route
from app.Http.Controllers.Admin.HomeController import HomeController
from app.Http.Controllers.Auth.AuthController import AuthController
from app.Http.Controllers.Blog.PostController import PostController
from app.Http.Controllers.Blog.DocsController import DocsController

# Home & Dashboard Routes
Route.get("/", [HomeController, "index"]).name("home")
Route.get("/home", [HomeController, "index"]).name("home.index")
Route.get("/dashboard", [HomeController, "index"]).name("dashboard")

# Authentication
Route.get("/login", [AuthController, "show_login"]).name("login")
Route.post("/login", [AuthController, "login"]).name("login.attempt")
Route.get("/register", [AuthController, "show_register"]).name("register")
Route.post("/register", [AuthController, "register"]).name("register.store")
Route.post("/logout", [AuthController, "logout"]).name("logout")

# Admin Route with auth middleware
Route.get("/admin", [HomeController, "admin"]).middleware("auth").name("admin.dashboard")

# Resource & Web Content Routes
Route.resource("posts", PostController)
Route.get("/docs", [DocsController, "index"]).name("docs.index")
Route.get("/docs/{page}", [DocsController, "show"]).name("docs.show")
