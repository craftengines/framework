"""Exception handler: status mapping, reporting policy and debug leakage."""
# Codepy Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import json

import pytest

from services.exceptions.handler import (
    AuthorizationException,
    CodepyException,
    ExceptionHandler,
    NotFoundHttpException,
    ValidationException,
)


class FakeConfig:
    def __init__(self, debug=False):
        self._debug = debug

    def get(self, key, default=None):
        if key in ("app.debug", "app.APP_DEBUG"):
            return self._debug
        return default


class FakeLogger:
    def __init__(self):
        self.errors = []
        self.infos = []

    def error(self, *args, **kwargs):
        self.errors.append((args, kwargs))

    def info(self, *args, **kwargs):
        self.infos.append((args, kwargs))


class FakeApp:
    def __init__(self, debug=False):
        self.config = FakeConfig(debug)
        self.logger = FakeLogger()

    def make(self, name):
        if name == "config":
            return self.config
        if name == "log":
            return self.logger
        raise KeyError(name)


@pytest.fixture
def app():
    return FakeApp()


@pytest.fixture
def handler(app):
    return ExceptionHandler(app)


class TestStatusMapping:
    @pytest.mark.parametrize(
        "exception,status",
        [
            (NotFoundHttpException("gone"), 404),
            (AuthorizationException("no"), 403),
            (ValidationException({"a": ["bad"]}), 422),
            (CodepyException("boom"), 500),
            (RuntimeError("unexpected"), 500),
        ],
    )
    def test_status_for(self, handler, exception, status):
        assert handler.status_for(exception) == status

    def test_validation_errors_reach_the_payload(self, handler):
        payload = handler.to_payload(ValidationException({"email": ["required"]}))
        assert payload["errors"] == {"email": ["required"]}


class TestReportingPolicy:
    def test_server_faults_are_logged_with_a_trace(self, handler, app):
        handler.report(RuntimeError("boom"))
        assert len(app.logger.errors) == 1
        assert app.logger.errors[0][1].get("exc_info") is not None

    def test_client_errors_are_not_logged_as_faults(self, handler, app):
        # A failed CSRF check or a 404 is the client getting it wrong; a stack
        # trace for each one buries the real faults.
        error = CodepyException("CSRF token mismatch.")
        error.status_code = 419
        handler.report(error)

        assert app.logger.errors == []
        assert len(app.logger.infos) == 1

    def test_not_found_is_never_reported_as_a_fault(self, handler, app):
        handler.report(NotFoundHttpException("nope"))
        assert app.logger.errors == []

    def test_should_report_only_for_5xx(self, handler):
        assert handler.should_report(RuntimeError("boom")) is True
        assert handler.should_report(AuthorizationException("no")) is False


class TestDebugLeakage:
    def test_trace_is_hidden_when_debug_is_off(self, handler):
        assert "trace" not in handler.to_payload(RuntimeError("boom"))

    def test_trace_is_shown_when_debug_is_on(self):
        handler = ExceptionHandler(FakeApp(debug=True))
        payload = handler.to_payload(RuntimeError("boom"))
        assert "trace" in payload and "exception" in payload

    def test_render_returns_the_right_status(self, handler):
        response = handler.render(AuthorizationException("no"), wants_json=True)
        assert response.status_code == 403

    def test_json_render_carries_the_message(self, handler):
        response = handler.render(CodepyException("boom"), wants_json=True)
        assert json.loads(response.body)["message"] == "boom"

    def test_html_render_hides_the_trace_without_debug(self, handler):
        response = handler.render(RuntimeError("boom"), wants_json=False)
        assert b"<pre>" not in response.body

    def test_handler_without_an_app_does_not_crash(self):
        assert ExceptionHandler().render(RuntimeError("boom"), True).status_code == 500
