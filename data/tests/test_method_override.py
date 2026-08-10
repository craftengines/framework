"""HTML form method spoofing via the `_method` field.

The framework emitted the hidden `_method` input from two places — the
`@method("PUT")` view directive and every edit/delete form the CRUD builder
generates — and read it from none. Browsers can only send GET and POST, so a
`Route.resource()` update (PUT) or destroy (DELETE) received a POST and
returned 405: the directive produced decorative HTML and generated admin forms
did not work at all. Existing tests only asserted the HTML string, never the
effect.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest
from starlette.testclient import TestClient

from bootstrap.app import asgi_app
from craft.facades import Route


@pytest.fixture(scope="module", autouse=True)
def override_routes(migrated_database):
    def updated(request):
        return {"verb": "PUT", "payload": request.input("title")}

    def destroyed(request):
        return {"verb": "DELETE"}

    def created(request):
        return {"verb": "POST"}

    def token(request):
        return {"token": request.session().token()}

    Route.put("/t-override/thing", updated).name("t.override.put")
    Route.delete("/t-override/thing", destroyed).name("t.override.delete")
    Route.post("/t-override/plain", created).name("t.override.post")
    Route.get("/t-override/token", token).name("t.override.token")
    yield


@pytest.fixture
def client():
    return TestClient(asgi_app)


@pytest.fixture
def csrf(client):
    """CSRF still applies to the spoofed verb — the override runs before the
    middleware, so a PUT is verified exactly like any other write."""
    return client.get("/t-override/token").json()["token"]


class TestUrlEncodedForms:
    def test_a_post_with_method_put_reaches_the_put_route(self, client, csrf):
        response = client.post(
            "/t-override/thing",
            data={"_method": "PUT", "title": "hello", "_token": csrf},
            headers={"Accept": "application/json"},
        )
        assert response.status_code == 200
        assert response.json()["verb"] == "PUT"

    def test_the_rest_of_the_form_survives_the_override(self, client, csrf):
        """The body is buffered to read `_method`; it must still be readable
        by the controller afterwards."""
        response = client.post(
            "/t-override/thing",
            data={"_method": "PUT", "title": "hello", "_token": csrf},
            headers={"Accept": "application/json"},
        )
        assert response.json()["payload"] == "hello"

    def test_a_post_with_method_delete_reaches_the_delete_route(self, client, csrf):
        response = client.post(
            "/t-override/thing",
            data={"_method": "DELETE", "_token": csrf},
            headers={"Accept": "application/json"},
        )
        assert response.status_code == 200
        assert response.json()["verb"] == "DELETE"

    def test_lowercase_is_accepted(self, client, csrf):
        response = client.post(
            "/t-override/thing",
            data={"_method": "put", "_token": csrf},
            headers={"Accept": "application/json"},
        )
        assert response.json()["verb"] == "PUT"


class TestMultipartForms:
    def test_method_override_works_in_multipart(self, client, csrf):
        """The CRUD builder's edit form carries a file input whenever the
        entity has one, which switches the encoding to multipart."""
        response = client.post(
            "/t-override/thing",
            data={"_method": "PUT", "title": "multi", "_token": csrf},
            files={"attachment": ("note.txt", b"contents", "text/plain")},
            headers={"Accept": "application/json"},
        )
        assert response.status_code == 200
        assert response.json()["verb"] == "PUT"


class TestItDoesNotOverreach:
    def test_a_plain_post_is_left_alone(self, client, csrf):
        response = client.post(
            "/t-override/plain",
            data={"title": "no override here", "_token": csrf},
            headers={"Accept": "application/json"},
        )
        assert response.json()["verb"] == "POST"

    def test_an_unspoofable_verb_is_ignored(self, client, csrf):
        """Only PUT/PATCH/DELETE may be spoofed. Letting `_method=GET` through
        would turn a POST into a GET and skip CSRF verification entirely."""
        response = client.post(
            "/t-override/plain",
            data={"_method": "GET", "_token": csrf},
            headers={"Accept": "application/json"},
        )
        assert response.json()["verb"] == "POST"

    def test_a_json_body_is_not_scanned_for_method(self, client, csrf):
        """Only form encodings carry `_method`; a JSON API must not have its
        verb rewritten by a field that happens to be named that."""
        response = client.post(
            "/t-override/plain",
            json={"_method": "DELETE", "_token": csrf},
            headers={"Accept": "application/json", "X-CSRF-TOKEN": csrf},
        )
        assert response.json()["verb"] == "POST"
