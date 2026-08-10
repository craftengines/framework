"""The admin surface must be closed to ordinary users.

`GET /admin` renders the dashboard that lists **every user, every administrator
and every tenant** in the installation. It shipped carrying the `auth` alias
alone, so any account that could log in — the seeded `user@craft.local`
included — read the whole directory. Every *other* admin route already required
`role:admin`; this one was missed, which is exactly why the structural test at
the bottom exists: a human reviewer comparing route declarations by eye is not
a control.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest
from starlette.testclient import TestClient

from bootstrap.app import app, asgi_app
from craft.facades import DB, Route

#: Route middleware that actually authorizes. `auth` only proves *who* you are;
#: on an admin page, identity without authorization is the bug itself.
AUTHORIZING_ALIASES = ("role:", "permission:", "group:", "can:")


@pytest.fixture(scope="module", autouse=True)
def helper_routes(migrated_database):
    """A token endpoint and a login endpoint, so the suite can hold a session."""

    def token(request):
        return {"token": request.session().token()}

    def do_login(request):
        ok = app.make("auth").attempt(
            {"email": request.input("email"), "password": request.input("password")}
        )
        return {"ok": ok}

    Route.get("/t/admin/token", token).name("t.admin.token")
    Route.post("/t/admin/login", do_login).name("t.admin.login")
    yield


@pytest.fixture
def client():
    return TestClient(asgi_app)


@pytest.fixture
def accounts(migrated_database):
    """A plain user and an administrator, wired to the real `admin` role."""
    from app.Models.Role import Role
    from app.Models.User import User

    for email in ("plain-admintest@craft.local", "admin-admintest@craft.local"):
        DB.statement("DELETE FROM users WHERE email = ?", [email])

    plain = User.create({
        "name": "Plain", "email": "plain-admintest@craft.local", "password": "s3cret",
    })
    administrator = User.force_create({
        "name": "Boss", "email": "admin-admintest@craft.local", "password": "s3cret",
        "is_admin": True,
    })

    role = Role.query().where("slug", "admin").first()
    if role is None:
        role = Role.create({"name": "Admin", "slug": "admin"})
    DB.statement(
        "INSERT INTO role_user (user_id, role_id) VALUES (:user, :role)",
        {"user": administrator.get_attribute("id"), "role": role.get_attribute("id")},
    )
    return {"plain": plain, "admin": administrator}


def login(client, email: str, password: str = "s3cret") -> None:
    token = client.get("/t/admin/token").json()["token"]
    client.post("/t/admin/login", data={"email": email, "password": password, "_token": token})


def admin_routes():
    """Every registered route whose path is under `/admin`."""
    router = app.make("router")
    return [r for r in router.routes if r.uri == "/admin" or r.uri.startswith("/admin/")]


class TestOrdinaryUsersCannotReachTheAdminSurface:
    def test_a_logged_in_user_cannot_read_the_admin_dashboard(self, client, accounts):
        """The reported failure: log in as an ordinary user, see the directory."""
        login(client, "plain-admintest@craft.local")

        response = client.get(
            "/admin", headers={"Accept": "application/json"}, follow_redirects=False
        )
        assert response.status_code == 403, (
            "an ordinary authenticated user reached the admin dashboard, which "
            "lists every user, administrator and tenant"
        )

    def test_no_admin_route_answers_an_ordinary_user(self, client, accounts):
        login(client, "plain-admintest@craft.local")

        reachable = []
        for route in admin_routes():
            if "GET" not in route.methods:
                continue
            response = client.get(
                route.uri, headers={"Accept": "application/json"}, follow_redirects=False
            )
            if response.status_code == 200:
                reachable.append(route.uri)

        assert reachable == [], f"ordinary user reached: {reachable}"

    def test_a_guest_is_sent_to_the_login_page(self, client, accounts):
        response = client.get("/admin", follow_redirects=False)
        assert response.status_code in (302, 401, 403)


class TestAdministratorsStillGetIn:
    def test_the_dashboard_answers_an_administrator(self, client, accounts):
        """The fix must close the hole without closing the door."""
        login(client, "admin-admintest@craft.local")

        response = client.get("/admin", follow_redirects=False)
        assert response.status_code == 200

    def test_every_admin_page_renders_for_an_administrator(self, client, accounts):
        """Locking a page down and breaking it look identical from outside.

        A 500 here means the template or the controller is broken — which the
        authorization tests above would happily report as "not 200", i.e. as
        success.
        """
        login(client, "admin-admintest@craft.local")

        broken = []
        for route in admin_routes():
            if "GET" not in route.methods:
                continue
            response = client.get(route.uri, follow_redirects=False)
            if response.status_code != 200:
                broken.append((route.uri, response.status_code))

        assert broken == [], f"admin pages not rendering for an administrator: {broken}"


class TestEveryAdminRouteIsAuthorized:
    """The structural guard.

    The dashboard was not left open by a wrong decision — it was left open by a
    route declaration that nobody compared against its neighbours. This test
    makes that comparison mechanical, so the next `/admin` route added without
    authorization fails here instead of in production.
    """

    def test_admin_routes_declare_authorization_not_just_authentication(self):
        unguarded = []
        for route in admin_routes():
            declared = [m for m in route.middleware_list if isinstance(m, str)]
            if not any(m.startswith(AUTHORIZING_ALIASES) for m in declared):
                unguarded.append((route.uri, declared))

        assert unguarded == [], (
            "these /admin routes carry no authorization middleware — `auth` "
            f"alone only proves who the visitor is: {unguarded}"
        )

    def test_admin_routes_require_authentication_too(self):
        unauthenticated = [
            route.uri
            for route in admin_routes()
            if "auth" not in [m for m in route.middleware_list if isinstance(m, str)]
        ]
        assert unauthenticated == []
