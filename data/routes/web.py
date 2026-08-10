"""Web routes for Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.facades import Route
from app.Http.Controllers.Admin.HomeController import HomeController
from app.Http.Controllers.Admin.CrudBuilderController import CrudBuilderController
from app.Http.Controllers.Admin.GroupController import GroupController
from app.Http.Controllers.Admin.RoleController import RoleController, PermissionController
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

# The dashboard lists every user, every administrator and every tenant in the
# installation. It carried `auth` alone, so any account that could log in read
# the whole directory — authentication is not authorization. `role:admin` puts
# it on the same footing as the rest of the admin surface, and
# `tests/test_admin_authorization.py` now fails the build if any /admin route
# is ever declared without an authorizing alias again.
Route.get("/admin", [HomeController, "admin"]).middleware("auth", "role:admin").name("admin.dashboard")

# The CRUD builder writes real `.py` files into app/ and database/migrations/
# and rewrites routes/api.py and routes/web.py. Behind `auth` alone that is
# remote code execution for any registered user, so it carries `role:admin`
# like the rest of the admin surface.
Route.get("/admin/crud-builder", [CrudBuilderController, "index"]).middleware("auth", "role:admin").name("admin.crud_builder.index")
Route.post("/admin/crud-builder", [CrudBuilderController, "store"]).middleware("auth", "role:admin").name("admin.crud_builder.store")

# RBAC admin UI — the first real usage of the `role:<slug>` route middleware.
Route.get("/admin/roles", [RoleController, "index"]).middleware("auth", "role:admin").name("admin.roles.index")
Route.post("/admin/roles/grant", [RoleController, "grant"]).middleware("auth", "role:admin").name("admin.roles.grant")
Route.get("/admin/permissions", [PermissionController, "index"]).middleware("auth", "role:admin").name("admin.permissions.index")

# Group admin UI — team-level access, plus the conditional (ABAC) grants.
# Every one of these hands out access, so they are themselves admin-only.
Route.get("/admin/groups", [GroupController, "index"]).middleware("auth", "role:admin").name("admin.groups.index")
Route.post("/admin/groups", [GroupController, "store"]).middleware("auth", "role:admin").name("admin.groups.store")
Route.post("/admin/groups/members", [GroupController, "add_member"]).middleware("auth", "role:admin").name("admin.groups.members")
Route.post("/admin/groups/roles", [GroupController, "grant_role"]).middleware("auth", "role:admin").name("admin.groups.roles")
Route.post("/admin/groups/permissions", [GroupController, "grant_permission"]).middleware("auth", "role:admin").name("admin.groups.permissions")

# Resource & Web Content Routes
# Reads stay public; create/update/delete require a logged-in session (the
# controller additionally checks ownership via PostPolicy/Gate).
Route.resource("posts", PostController, write_middleware="auth")
Route.get("/docs", [DocsController, "index"]).name("docs.index")
Route.get("/docs/{page}", [DocsController, "show"]).name("docs.show")
