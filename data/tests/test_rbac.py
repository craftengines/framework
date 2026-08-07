"""RBAC enforcement — `has_role`, the Gate permission fallback, the
`role:<slug>`/`permission:<slug>` route middleware, and the seeded demo
accounts.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest
from starlette.testclient import TestClient

from bootstrap.app import app, asgi_app
from craft.facades import DB, Route


def _reset_rbac_tables():
    DB.statement("DELETE FROM permission_role")
    DB.statement("DELETE FROM role_user")
    DB.statement("DELETE FROM permissions")
    DB.statement("DELETE FROM roles")


@pytest.fixture
def rbac_user(migrated_database):
    from app.Models.User import User
    from app.Models.Role import Role
    from app.Models.Permission import Permission

    DB.statement("DELETE FROM users WHERE email = 'rbac@craft.local'")
    _reset_rbac_tables()

    user = User.create(
        {"name": "RBAC", "email": "rbac@craft.local", "password": "s3cret", "is_admin": False}
    )
    role = Role.create({"name": "Editor", "slug": "editor"})
    permission = Permission.create({"name": "Edit Posts", "slug": "edit-posts"})

    DB.statement(
        "INSERT INTO role_user (user_id, role_id) VALUES (:user, :role)",
        {"user": user.get_attribute("id"), "role": role.get_attribute("id")},
    )
    DB.statement(
        "INSERT INTO permission_role (role_id, permission_id) VALUES (:role, :perm)",
        {"role": role.get_attribute("id"), "perm": permission.get_attribute("id")},
    )
    return user


class TestHasRole:
    def test_has_role_true_for_granted_role(self, rbac_user):
        assert rbac_user.has_role("editor") is True

    def test_has_role_false_for_ungranted_role(self, rbac_user):
        assert rbac_user.has_role("admin") is False


class TestGatePermissionFallback:
    def test_gate_falls_back_to_the_permission_system(self, rbac_user):
        from services.auth.gate import GateManager

        gate = GateManager()
        # No ability closure, no policy registered for "edit-posts" — the
        # RBAC permission fallback must still grant it.
        assert gate.allows("edit-posts", rbac_user) is True

    def test_gate_still_denies_unknown_abilities_by_default(self, rbac_user):
        from services.auth.gate import GateManager

        gate = GateManager()
        assert gate.allows("nonexistent-ability", rbac_user) is False

    def test_ability_closures_still_take_priority(self, rbac_user):
        from services.auth.gate import GateManager

        gate = GateManager()
        gate.define("edit-posts", lambda user: False)
        # Even though the user *has* the permission, an explicit closure wins.
        assert gate.allows("edit-posts", rbac_user) is False

    def test_gate_tolerates_users_without_has_permission(self):
        from services.auth.gate import GateManager

        gate = GateManager()
        assert gate.allows("edit-posts", object()) is False


class TestKernelAliasResolution:
    def test_role_alias_resolves_with_its_parameter(self):
        from services.http.kernel import Kernel
        from services.http.middleware import RequireRole

        kernel = Kernel(app)
        [instance] = kernel.resolve_route_middleware(["role:admin"])
        assert isinstance(instance, RequireRole)
        assert instance.role == "admin"

    def test_permission_alias_resolves_with_its_parameter(self):
        from services.http.kernel import Kernel
        from services.http.middleware import RequirePermission

        kernel = Kernel(app)
        [instance] = kernel.resolve_route_middleware(["permission:manage-users"])
        assert isinstance(instance, RequirePermission)
        assert instance.permission == "manage-users"

    def test_bare_alias_without_parameter_still_works(self):
        from services.http.kernel import Kernel
        from services.http.middleware import RequireAuth

        kernel = Kernel(app)
        [instance] = kernel.resolve_route_middleware(["auth"])
        assert isinstance(instance, RequireAuth)

    def test_unknown_alias_raises(self):
        from services.http.kernel import Kernel

        kernel = Kernel(app)
        with pytest.raises(KeyError):
            kernel.resolve_route_middleware(["role"])  # no ":" separator, not a bare alias

        with pytest.raises(KeyError):
            kernel.resolve_route_middleware(["totally-unknown:param"])


@pytest.fixture(scope="module", autouse=True)
def rbac_routes(migrated_database):
    def only_admins(request):
        return {"ok": True}

    def only_editors(request):
        return {"ok": True}

    def token(request):
        return {"token": request.session().token()}

    def do_login(request):
        auth = app.make("auth")
        ok = auth.attempt(
            {"email": request.input("email"), "password": request.input("password")}
        )
        return {"ok": ok}

    Route.get("/t/rbac/admin-only", only_admins).middleware("role:admin").name("t.rbac.admin")
    Route.get("/t/rbac/edit-posts-only", only_editors).middleware(
        "permission:edit-posts"
    ).name("t.rbac.permission")
    Route.get("/t/rbac/token", token).name("t.rbac.token")
    Route.post("/t/rbac/login", do_login).name("t.rbac.login")
    yield


@pytest.fixture
def client():
    return TestClient(asgi_app)


def login(client, email: str, password: str) -> None:
    token = client.get("/t/rbac/token").json()["token"]
    client.post(
        "/t/rbac/login",
        data={"email": email, "password": password, "_token": token},
    )


class TestRequireRoleMiddleware:
    def test_guest_is_redirected(self, client):
        response = client.get("/t/rbac/admin-only", follow_redirects=False)
        assert response.status_code == 302

    def test_guest_gets_403_json_when_json_is_expected(self, client):
        response = client.get(
            "/t/rbac/admin-only", headers={"Accept": "application/json"}
        )
        assert response.status_code == 403

    def test_user_without_the_role_is_forbidden(self, client, rbac_user):
        login(client, "rbac@craft.local", "s3cret")
        response = client.get(
            "/t/rbac/admin-only", headers={"Accept": "application/json"}
        )
        assert response.status_code == 403

    def test_user_with_the_role_is_allowed(self, client, migrated_database):
        from app.Models.User import User
        from app.Models.Role import Role

        DB.statement("DELETE FROM users WHERE email = 'rbac-admin@craft.local'")
        user = User.create(
            {
                "name": "RBAC Admin",
                "email": "rbac-admin@craft.local",
                "password": "s3cret",
                "is_admin": False,
            }
        )
        role = Role.query().where("slug", "admin").first() or Role.create(
            {"name": "Administrator", "slug": "admin"}
        )
        DB.statement(
            "INSERT INTO role_user (user_id, role_id) VALUES (:user, :role)",
            {"user": user.get_attribute("id"), "role": role.get_attribute("id")},
        )

        login(client, "rbac-admin@craft.local", "s3cret")
        response = client.get("/t/rbac/admin-only")
        assert response.status_code == 200


class TestRequirePermissionMiddleware:
    def test_user_with_the_permission_is_allowed(self, client, rbac_user):
        login(client, "rbac@craft.local", "s3cret")
        response = client.get("/t/rbac/edit-posts-only")
        assert response.status_code == 200

    def test_user_without_the_permission_is_forbidden(self, client, migrated_database):
        from app.Models.User import User

        DB.statement("DELETE FROM users WHERE email = 'rbac-nobody@craft.local'")
        User.create(
            {
                "name": "Nobody",
                "email": "rbac-nobody@craft.local",
                "password": "s3cret",
                "is_admin": False,
            }
        )
        login(client, "rbac-nobody@craft.local", "s3cret")
        response = client.get(
            "/t/rbac/edit-posts-only", headers={"Accept": "application/json"}
        )
        assert response.status_code == 403


class TestSeededDemoAccountsHaveRoles:
    """The 3 seeded demo accounts must each carry a role — a tenant user with
    zero roles defeats the point of the 3-tier ladder."""

    def test_all_three_demo_users_have_a_role(self, migrated_database):
        from database.seeders.UserSeeder import UserSeeder
        from database.seeders.FrameworkSeeder import FrameworkSeeder
        from app.Models.User import User

        DB.statement("DELETE FROM permission_role")
        DB.statement("DELETE FROM role_user")
        DB.statement("DELETE FROM permissions")
        DB.statement("DELETE FROM roles")
        DB.statement("DELETE FROM users WHERE email IN "
                     "('user@craft.local', 'tenant@craft.local', 'admin@craft.local')")

        UserSeeder().run()
        FrameworkSeeder().run()

        plain_user = User.query().where("email", "user@craft.local").first()
        tenant_user = User.query().where("email", "tenant@craft.local").first()
        admin_user = User.query().where("email", "admin@craft.local").first()

        assert plain_user.has_role("user") is True
        assert tenant_user.has_role("tenant-manager") is True
        assert admin_user.has_role("admin") is True

        # The ladder: tenant-manager sits strictly between user and admin.
        assert tenant_user.has_permission("manage-users") is True
        assert plain_user.has_permission("manage-users") is False
