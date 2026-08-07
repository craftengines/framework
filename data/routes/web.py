"""Web routes for Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.facades import Route
from app.Http.Controllers.Admin.HomeController import HomeController
from app.Http.Controllers.Admin.CrudBuilderController import CrudBuilderController
from app.Http.Controllers.Auth.AuthController import AuthController
from app.Http.Controllers.Blog.PostController import PostController
from app.Http.Controllers.Blog.DocsController import DocsController

# Home & Dashboard Routes
Route.get("/", [HomeController, "index"]).name("home")
Route.get("/home", [HomeController, "index"]).name("home.index")
Route.get("/dashboard", [HomeController, "index"]).name("dashboard")

# Authentication — login/register are throttled per IP+route to close the
# brute-force gap: the CAPTCHA on /login stops naive scripted attempts, but
# does not bound automated ones without a request-rate limit.
Route.get("/login", [AuthController, "show_login"]).name("login")
Route.post("/login", [AuthController, "login"]).middleware("throttle").name("login.attempt")
Route.get("/register", [AuthController, "show_register"]).name("register")
Route.post("/register", [AuthController, "register"]).middleware("throttle").name("register.store")
Route.post("/logout", [AuthController, "logout"]).name("logout")

# Admin Route with auth middleware
Route.get("/admin", [HomeController, "admin"]).middleware("auth").name("admin.dashboard")
Route.get("/admin/crud-builder", [CrudBuilderController, "index"]).middleware("auth").name("admin.crud_builder.index")
Route.post("/admin/crud-builder", [CrudBuilderController, "store"]).middleware("auth").name("admin.crud_builder.store")

# Resource & Web Content Routes
# Reads stay public; create/update/delete require a logged-in session (the
# controller additionally checks ownership via PostPolicy/Gate).
Route.resource("posts", PostController, write_middleware="auth")
Route.get("/docs", [DocsController, "index"]).name("docs.index")
Route.get("/docs/{page}", [DocsController, "show"]).name("docs.show")
