"""Session, CSRF and authentication across real HTTP requests."""
# Codepy Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest
from starlette.testclient import TestClient

from bootstrap.app import app, asgi_app
from codepy.facades import DB, Route
from services.http.middleware import Authenticate


@pytest.fixture(scope="module", autouse=True)
def routes(migrated_database):
    """Register throwaway routes exercising the middleware stack."""

    def counter(request):
        session = request.session()
        count = int(session.get("count", 0)) + 1
        session.put("count", count)
        return {"count": count}

    def echo(request):
        return {"input": request.all()}

    def whoami(request):
        user = request.user()
        return {"user": user.get_attribute("email") if user else None}

    def token(request):
        return {"token": request.session().token()}

    def flash_write(request):
        request.session().flash("status", "saved")
        return {"ok": True}

    def flash_read(request):
        return {"status": request.session().get("status")}

    def do_login(request):
        auth = app.make("auth")
        ok = auth.attempt(
            {"email": request.input("email"), "password": request.input("password")}
        )
        return {"ok": ok}

    def do_logout(request):
        app.make("auth").logout()
        return {"ok": True}

    Route.get("/t/counter", counter).name("t.counter")
    Route.get("/t/token", token).name("t.token")
    Route.get("/t/whoami", whoami).name("t.whoami")
    Route.get("/t/flash-read", flash_read).name("t.flash.read")
    Route.post("/t/echo", echo).name("t.echo")
    Route.post("/t/flash-write", flash_write).name("t.flash.write")
    Route.post("/t/login", do_login).name("t.login")
    Route.post("/t/logout", do_logout).name("t.logout")
    Route.post("/api/t/echo", echo).name("t.api.echo")
    yield


@pytest.fixture
def client():
    return TestClient(asgi_app)


@pytest.fixture
def user(migrated_database):
    from app.Models.User import User

    DB.statement("DELETE FROM users WHERE email = 'mw@codepy.local'")
    return User.create(
        {"name": "MW", "email": "mw@codepy.local", "password": "s3cret", "is_admin": False}
    )


def csrf_for(client) -> str:
    return client.get("/t/token").json()["token"]


class TestSessionAcrossRequests:
    def test_a_session_cookie_is_issued(self, client):
        response = client.get("/t/counter")
        assert "codepy_session" in response.cookies

    def test_values_persist_between_requests(self, client):
        assert client.get("/t/counter").json()["count"] == 1
        assert client.get("/t/counter").json()["count"] == 2
        assert client.get("/t/counter").json()["count"] == 3

    def test_separate_clients_get_separate_sessions(self, client):
        other = TestClient(asgi_app)
        client.get("/t/counter")
        client.get("/t/counter")
        assert other.get("/t/counter").json()["count"] == 1

    def test_the_cookie_is_http_only(self, client):
        response = client.get("/t/counter")
        assert "httponly" in response.headers["set-cookie"].lower()

    def test_flash_data_lives_exactly_one_request(self, client):
        token = csrf_for(client)
        client.post("/t/flash-write", data={"_token": token})
        assert client.get("/t/flash-read").json()["status"] == "saved"
        assert client.get("/t/flash-read").json()["status"] is None


class TestCsrf:
    def test_post_without_a_token_is_rejected(self, client):
        client.get("/t/token")  # establish a session
        assert client.post("/t/echo", data={"a": "1"}).status_code == 419

    def test_post_with_the_form_token_is_accepted(self, client):
        token = csrf_for(client)
        response = client.post("/t/echo", data={"a": "1", "_token": token})
        assert response.status_code == 200

    def test_post_with_the_header_token_is_accepted(self, client):
        token = csrf_for(client)
        response = client.post("/t/echo", data={"a": "1"}, headers={"X-CSRF-TOKEN": token})
        assert response.status_code == 200

    def test_a_wrong_token_is_rejected(self, client):
        csrf_for(client)
        response = client.post("/t/echo", data={"_token": "forged"})
        assert response.status_code == 419

    def test_another_sessions_token_is_rejected(self, client):
        stolen = csrf_for(TestClient(asgi_app))
        csrf_for(client)
        assert client.post("/t/echo", data={"_token": stolen}).status_code == 419

    def test_get_requests_are_never_checked(self, client):
        assert client.get("/t/counter").status_code == 200

    def test_api_routes_are_exempt(self, client):
        response = client.post("/api/t/echo", json={"a": "1"})
        assert response.status_code == 200


class TestRequestInput:
    def test_form_body_is_parsed(self, client):
        token = csrf_for(client)
        response = client.post("/t/echo", data={"name": "jane", "_token": token})
        assert response.json()["input"]["name"] == "jane"

    def test_json_body_is_parsed(self, client):
        response = client.post("/api/t/echo", json={"name": "jane", "age": 30})
        assert response.json()["input"] == {"name": "jane", "age": 30}

    def test_query_string_is_merged(self, client):
        response = client.post("/api/t/echo?source=web", json={"name": "jane"})
        assert response.json()["input"]["source"] == "web"

    def test_malformed_json_does_not_crash(self, client):
        response = client.post(
            "/api/t/echo", content=b"{not json", headers={"content-type": "application/json"}
        )
        assert response.status_code == 200
        assert response.json()["input"] == {}


class TestAuthenticationAcrossRequests:
    def test_a_guest_has_no_user(self, client):
        assert client.get("/t/whoami").json()["user"] is None

    def test_login_survives_the_next_request(self, client, user):
        token = csrf_for(client)
        assert client.post(
            "/t/login",
            data={"email": "mw@codepy.local", "password": "s3cret", "_token": token},
        ).json()["ok"] is True

        # The real proof: a *separate* request still knows who we are.
        assert client.get("/t/whoami").json()["user"] == "mw@codepy.local"

    def test_wrong_password_does_not_authenticate(self, client, user):
        token = csrf_for(client)
        client.post(
            "/t/login",
            data={"email": "mw@codepy.local", "password": "wrong", "_token": token},
        )
        assert client.get("/t/whoami").json()["user"] is None

    def test_logout_ends_the_session(self, client, user):
        token = csrf_for(client)
        client.post(
            "/t/login",
            data={"email": "mw@codepy.local", "password": "s3cret", "_token": token},
        )
        assert client.get("/t/whoami").json()["user"] == "mw@codepy.local"

        client.post("/t/logout", data={"_token": csrf_for(client)})
        assert client.get("/t/whoami").json()["user"] is None

    def test_one_clients_login_does_not_leak_to_another(self, client, user):
        token = csrf_for(client)
        client.post(
            "/t/login",
            data={"email": "mw@codepy.local", "password": "s3cret", "_token": token},
        )
        stranger = TestClient(asgi_app)
        assert stranger.get("/t/whoami").json()["user"] is None

    def test_a_deleted_user_does_not_stay_authenticated(self, client, user):
        token = csrf_for(client)
        client.post(
            "/t/login",
            data={"email": "mw@codepy.local", "password": "s3cret", "_token": token},
        )
        DB.statement("DELETE FROM users WHERE email = 'mw@codepy.local'")
        assert client.get("/t/whoami").json()["user"] is None

    def test_login_rotates_the_session_id(self, client, user):
        before = client.get("/t/token")
        cookie_before = before.cookies.get("codepy_session")

        token = csrf_for(client)
        after = client.post(
            "/t/login",
            data={"email": "mw@codepy.local", "password": "s3cret", "_token": token},
        )
        assert after.cookies.get("codepy_session") != cookie_before


class TestAuthMiddlewareUnits:
    def test_session_key_is_what_the_manager_writes(self, migrated_database, user):
        auth = migrated_database.make("auth")
        from services.http.session import Session

        session = Session()
        auth.set_session(session)
        auth.login(user)

        assert session.get(Authenticate.SESSION_KEY) == user.get_attribute("id")

        auth.logout()
        assert session.get(Authenticate.SESSION_KEY) is None

    def test_reset_clears_memory_without_ending_the_session(self, migrated_database, user):
        auth = migrated_database.make("auth")
        from services.http.session import Session

        session = Session()
        auth.set_session(session)
        auth.login(user)
        auth.reset()

        assert auth.check() is False
        # reset() must not erase the key the middleware is about to read.
        assert session.get(Authenticate.SESSION_KEY) == user.get_attribute("id")
