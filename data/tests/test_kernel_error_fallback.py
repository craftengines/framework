"""Without an exception handler the kernel never echoes exception text."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import json
from types import SimpleNamespace

from craft.http.kernel import render_exception


def _app_without_handler() -> SimpleNamespace:
    def make(key: str) -> None:
        raise KeyError(key)

    return SimpleNamespace(make=make)


def test_server_error_body_carries_no_exception_detail() -> None:
    leak = RuntimeError('duplicate key value violates unique constraint DETAIL: Key (email)=(a@b.c)')
    response = render_exception(_app_without_handler(), SimpleNamespace(), leak)
    body = json.loads(response.body)
    assert response.status_code == 500
    assert body == {"error": {"code": "SERVER_ERROR", "message_key": "error.server"}}
    assert "a@b.c" not in response.body.decode()


def test_client_error_keeps_its_stable_code_and_key() -> None:
    class Conflict(Exception):
        status_code = 409
        code = "ORDER_ALREADY_PAID"
        message_key = "order.checkout.already_paid"

    response = render_exception(_app_without_handler(), SimpleNamespace(), Conflict("internal detail"))
    assert response.status_code == 409
    assert json.loads(response.body)["error"] == {
        "code": "ORDER_ALREADY_PAID",
        "message_key": "order.checkout.already_paid",
    }
    assert "internal detail" not in response.body.decode()
