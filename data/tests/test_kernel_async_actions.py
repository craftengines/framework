"""Async controller actions run on the request's own worker thread.

The pooled database connection is thread-local and `release()` runs on the
thread that served the request. Running the coroutine on a separate executor
thread used to check out a second connection that nothing ever released.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import threading

import pytest
from starlette.testclient import TestClient

from bootstrap.app import app, asgi_app
from craft.facades import DB, Route


@pytest.fixture(scope="module", autouse=True)
def routes(migrated_database):
    async def which_thread(request):
        DB.select("SELECT 1")
        return {"thread": threading.current_thread().name}

    Route.get("/t/async-thread", which_thread).name("t.async.thread")
    yield


def test_async_action_runs_on_the_request_thread():
    client = TestClient(asgi_app)
    name = client.get("/t/async-thread").json()["thread"]
    assert not name.startswith("ThreadPoolExecutor")


def test_async_action_leaves_no_connection_checked_out():
    client = TestClient(asgi_app)
    connection = app.make("db").write_connection
    for _ in range(3):
        assert client.get("/t/async-thread").status_code == 200
    assert connection.open_sessions <= 1
