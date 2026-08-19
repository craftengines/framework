"""Test Identity & RBAC Lifecycle: Architecture Decoupling, Self-Service, and RBAC Automation.

Category: Tests (Identity & RBAC Lifecycle).
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest
from starlette.testclient import TestClient

from bootstrap.app import app, asgi_app
from craft.facades import Auth, DB, Hash, Route
from app.Models.User import User
from app.Models.Role import Role
from app.Models.Group import Group
from app.Models.Permission import Permission
from app.Services.Identity.DomainValidator import DomainValidator


@pytest.fixture(scope="module", autouse=True)
def auth_helper_routes(migrated_database):
    """Helper endpoints to facilitate session authentication in tests."""
    def token(request):
        return {"token": request.session().token()}

    def do_login(request):
        ok = app.make("auth").attempt({
            "email": request.input("email"),
            "password": request.input("password"),
        })
        return {"ok": ok}

    Route.get("/t/identity/token", token).name("t.identity.token")
    Route.post("/t/identity/login", do_login).name("t.identity.login")
    yield


@pytest.fixture
def client():
    return TestClient(asgi_app)


@pytest.fixture
def test_accounts(migrated_database):
    """Create a standard user and an admin user for lifecycle testing."""
    for email in ("member-lifecycle@craft.local", "admin-lifecycle@craft.local", "other-user@craft.local"):
        DB.statement("DELETE FROM users WHERE email = ?", [email])

    member = User.create({
        "name": "Standard Member",
        "email": "member-lifecycle@craft.local",
        "password": "initial_password_123",
    })

    admin = User.force_create({
        "name": "Admin Operator",
        "email": "admin-lifecycle@craft.local",
        "password": "admin_password_123",
        "is_admin": True,
    })

    role = Role.query().where("slug", "admin").first() or Role.create({"name": "Admin", "slug": "admin"})
    DB.statement(
        "INSERT INTO role_user (user_id, role_id) VALUES (?, ?)",
        [admin.get_attribute("id"), role.get_attribute("id")],
    )

    return {"member": member, "admin": admin}


def session_login(client, email: str, password: str) -> None:
    token_resp = client.get("/t/identity/token")
    token = token_resp.json()["token"]
    client.post("/t/identity/login", data={"email": email, "password": password, "_token": token})


# ==============================================================================
# Phase 1: User Architecture Decoupling & Domain Validation
# ==============================================================================

class TestDomainValidatorAndModelDecoupling:
    def test_domain_validator_format_and_system_overrides(self):
        assert DomainValidator.is_valid_format("user@craft.local") is True
        assert DomainValidator.is_valid_format("invalid-email") is False
        assert DomainValidator.is_valid_format("") is False

        # System domains are permitted
        assert DomainValidator.is_allowed_email("admin@system.local", allow_system_domains=True) is True
        assert DomainValidator.is_allowed_email("test@test.internal", allow_system_domains=True) is True
        assert DomainValidator.is_allowed_email("demo@craft.local", allow_system_domains=True) is True

    def test_user_model_automatic_hashing(self):
        email = "hash-check@craft.local"
        DB.statement("DELETE FROM users WHERE email = ?", [email])
        user = User.force_create({
            "name": "Hash Check",
            "email": email,
            "password": "PlainTextPassword!",
        })
        assert user.get_attribute("password") != "PlainTextPassword!"
        assert Hash.is_hashed(user.get_attribute("password")) is True
        assert user.check_password("PlainTextPassword!") is True
        assert user.check_password("WrongPassword") is False

    def test_operational_provisioning_without_external_coupling(self):
        """Demo, testing, and operational accounts can be provisioned freely without HR constraints."""
        email = "demo-contractless@test.internal"
        DB.statement("DELETE FROM users WHERE email = ?", [email])
        user = User.force_create({
            "name": "Demo Account",
            "email": email,
            "password": "DemoPassword123!",
            "is_admin": False,
        })
        assert user.get_attribute("id") is not None
        assert user.get_attribute("email") == email


# ==============================================================================
# Phase 2: Self-Service Profile & Credential Management
# ==============================================================================

class TestProfileSelfServiceAndCredentialRotation:
    def test_authenticated_user_can_view_profile(self, client, test_accounts):
        session_login(client, "member-lifecycle@craft.local", "initial_password_123")
        res = client.get("/panel/profile")
        assert res.status_code == 200
        assert "My profile" in res.text
        assert "Standard Member" in res.text
        assert "member-lifecycle@craft.local" in res.text

    def test_authenticated_user_can_update_profile_details(self, client, test_accounts):
        session_login(client, "member-lifecycle@craft.local", "initial_password_123")
        token = client.get("/t/identity/token").json()["token"]

        res = client.post(
            "/panel/profile",
            data={
                "name": "Updated Member Name",
                "email": "member-lifecycle@craft.local",
                "_token": token,
            },
            follow_redirects=False,
        )
        assert res.status_code == 302
        assert "success=profile_updated" in res.headers.get("location", "")

        refreshed = User.find(test_accounts["member"].get_attribute("id"))
        assert refreshed.get_attribute("name") == "Updated Member Name"

    def test_user_cannot_take_existing_email_on_profile_update(self, client, test_accounts):
        User.force_create({"name": "Existing", "email": "other-user@craft.local", "password": "pass"})

        session_login(client, "member-lifecycle@craft.local", "initial_password_123")
        token = client.get("/t/identity/token").json()["token"]

        res = client.post(
            "/panel/profile",
            data={
                "name": "Updated Member Name",
                "email": "other-user@craft.local",
                "_token": token,
            },
            follow_redirects=False,
        )
        assert res.status_code == 302
        assert "error=email_taken" in res.headers.get("location", "")

    def test_authenticated_user_can_rotate_password(self, client, test_accounts):
        session_login(client, "member-lifecycle@craft.local", "initial_password_123")
        token = client.get("/t/identity/token").json()["token"]

        # Wrong current password fails
        res_fail = client.post(
            "/panel/profile/password",
            data={
                "current_password": "wrong_password",
                "new_password": "new_secret_password_456",
                "new_password_confirmation": "new_secret_password_456",
                "_token": token,
            },
            follow_redirects=False,
        )
        assert res_fail.status_code == 302
        assert "error=invalid_current_password" in res_fail.headers.get("location", "")

        # Correct rotation succeeds
        res_ok = client.post(
            "/panel/profile/password",
            data={
                "current_password": "initial_password_123",
                "new_password": "new_secret_password_456",
                "new_password_confirmation": "new_secret_password_456",
                "_token": token,
            },
            follow_redirects=False,
        )
        assert res_ok.status_code == 302
        assert "success=password_updated" in res_ok.headers.get("location", "")

        refreshed = User.find(test_accounts["member"].get_attribute("id"))
        assert refreshed.check_password("new_secret_password_456") is True


# ==============================================================================
# Phase 3: Administrative User Management & RBAC Assignment
# ==============================================================================

class TestAdminUserManagementAndRBACLifecycle:
    def test_admin_can_provision_new_user_and_assign_role(self, client, test_accounts):
        session_login(client, "admin-lifecycle@craft.local", "admin_password_123")
        token = client.get("/t/identity/token").json()["token"]

        new_email = "provisioned-dev@craft.local"
        DB.statement("DELETE FROM users WHERE email = ?", [new_email])

        test_role = Role.query().where("slug", "dev-role").first() or Role.create({
            "name": "Developer Role",
            "slug": "dev-role",
        })

        res = client.post(
            "/panel/users",
            data={
                "name": "Provisioned Dev",
                "email": new_email,
                "password": "developer_password_123",
                "role_id": str(test_role.get_attribute("id")),
                "is_admin": "0",
                "_token": token,
            },
            follow_redirects=False,
        )
        assert res.status_code == 302
        assert "success=user_created" in res.headers.get("location", "")

        created_user = User.query().where("email", new_email).first()
        assert created_user is not None
        assert created_user.has_role("dev-role") is True

    def test_admin_can_assign_and_revoke_role_dynamically(self, client, test_accounts):
        session_login(client, "admin-lifecycle@craft.local", "admin_password_123")
        token = client.get("/t/identity/token").json()["token"]

        member = test_accounts["member"]
        manager_role = Role.query().where("slug", "manager-role").first() or Role.create({
            "name": "Manager Role",
            "slug": "manager-role",
        })

        u_id = member.get_attribute("id")
        r_id = manager_role.get_attribute("id")

        # Assign Role
        res_assign = client.post(
            "/panel/users/roles/assign",
            data={"user_id": str(u_id), "role_id": str(r_id), "_token": token},
            follow_redirects=False,
        )
        assert res_assign.status_code == 302
        assert member.has_role("manager-role") is True

        # Revoke Role
        res_revoke = client.post(
            "/panel/users/roles/revoke",
            data={"user_id": str(u_id), "role_id": str(r_id), "_token": token},
            follow_redirects=False,
        )
        assert res_revoke.status_code == 302
        assert member.has_role("manager-role") is False

    def test_non_admin_cannot_execute_admin_user_actions(self, client, test_accounts):
        session_login(client, "member-lifecycle@craft.local", "new_secret_password_456")
        token = client.get("/t/identity/token").json()["token"]

        res = client.post(
            "/panel/users",
            data={
                "name": "Hacker Attempt",
                "email": "hacker@evil.local",
                "password": "password123",
                "_token": token,
            },
            headers={"Accept": "application/json"},
            follow_redirects=False,
        )
        assert res.status_code == 403


# ==============================================================================
# Phase 4: End-to-End 4-Tier Access Resolution
# ==============================================================================

class TestFourTierAccessResolverDelegation:
    def test_end_to_end_permission_paths(self):
        from craft.container.application import Container

        access = Container.getInstance().make("access")
        email = "access-resolver-test@craft.local"
        DB.statement("DELETE FROM users WHERE email = ?", [email])

        user = User.force_create({"name": "Resolver Subject", "email": email, "password": "Password!"})
        role = Role.create({"name": "Content Creator", "slug": "content-creator"})
        group = Group.create({"name": "Marketing Team", "slug": "marketing-team"})

        p_direct = Permission.create({"name": "Direct Perm", "slug": "direct-perm"})
        p_role = Permission.create({"name": "Role Perm", "slug": "role-perm"})
        p_group_role = Permission.create({"name": "Group Role Perm", "slug": "group-role-perm"})
        p_group_direct = Permission.create({"name": "Group Direct Perm", "slug": "group-direct-perm"})

        u_id = user.get_attribute("id")
        r_id = role.get_attribute("id")
        g_id = group.get_attribute("id")

        # 1. Direct user -> permission
        DB.statement("INSERT INTO permission_user (user_id, permission_id) VALUES (?, ?)", [u_id, p_direct.get_attribute("id")])

        # 2. User -> Role -> Permission
        DB.statement("INSERT INTO role_user (user_id, role_id) VALUES (?, ?)", [u_id, r_id])
        DB.statement("INSERT INTO permission_role (role_id, permission_id) VALUES (?, ?)", [r_id, p_role.get_attribute("id")])

        # 3. User -> Group -> Role -> Permission
        group_role = Role.create({"name": "Group Sub Role", "slug": "group-sub-role"})
        DB.statement("INSERT INTO group_user (user_id, group_id) VALUES (?, ?)", [u_id, g_id])
        DB.statement("INSERT INTO group_role (group_id, role_id) VALUES (?, ?)", [g_id, group_role.get_attribute("id")])
        DB.statement("INSERT INTO permission_role (role_id, permission_id) VALUES (?, ?)", [group_role.get_attribute("id"), p_group_role.get_attribute("id")])

        # 4. User -> Group -> Permission (Direct to group)
        DB.statement("INSERT INTO permission_group (group_id, permission_id) VALUES (?, ?)", [g_id, p_group_direct.get_attribute("id")])

        # Verify all 4 tiers resolve unconditionally
        assert access.allows(user, "direct-perm") is True
        assert access.allows(user, "role-perm") is True
        assert access.allows(user, "group-role-perm") is True
        assert access.allows(user, "group-direct-perm") is True
        assert access.allows(user, "non-existent-perm") is False

        # Verify model delegation methods
        assert user.has_permission("direct-perm") is True
        assert user.has_permission("role-perm") is True
        assert user.has_permission("group-role-perm") is True
        assert user.has_permission("group-direct-perm") is True
        assert user.has_role("content-creator") is True
        assert user.has_role("group-sub-role") is True
        assert user.in_group("marketing-team") is True
