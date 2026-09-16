"""Scoped bindings live for one request and never leak into the next."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import itertools

import pytest
from starlette.testclient import TestClient

from bootstrap.app import app, asgi_app
from craft.container.application import Container
from craft.facades import Route

_counter = itertools.count(1)


class RequestState:
    """A per-request object; each instance carries a distinct serial number."""

    def __init__(self) -> None:
        self.serial = next(_counter)


@pytest.fixture(scope="module", autouse=True)
def routes(migrated_database):
    app.scoped(RequestState)

    def show_state(request):
        first = app.make(RequestState)
        second = app.make(RequestState)
        return {"serial": first.serial, "same_within_request": first is second}

    Route.get("/t/request-scope", show_state).name("t.request_scope")
    yield


def test_the_same_instance_is_shared_within_one_request() -> None:
    assert TestClient(asgi_app).get("/t/request-scope").json()["same_within_request"] is True


def test_each_request_gets_a_fresh_instance() -> None:
    client = TestClient(asgi_app)
    first = client.get("/t/request-scope").json()["serial"]
    second = client.get("/t/request-scope").json()["serial"]
    assert first != second


def test_a_request_scope_does_not_touch_the_outer_scope() -> None:
    container = Container()
    container.scoped(RequestState)
    outer = container.make(RequestState)
    token = Container.begin_request_scope()
    try:
        inner = container.make(RequestState)
        assert inner is not outer
        container.forget_scoped_instances()
        assert container.make(RequestState) is not inner
    finally:
        Container.end_request_scope(token)
    assert container.make(RequestState) is outer


def test_binding_a_class_to_itself_builds_it() -> None:
    container = Container()
    container.bind(RequestState)
    assert isinstance(container.make(RequestState), RequestState)
