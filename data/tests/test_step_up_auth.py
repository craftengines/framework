"""Step-up auth: freshness tracking, the fail-closed default, and the
RequireFreshAuth route middleware wired via the `fresh` alias.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import time

import pytest

from craft.auth.step_up import DEFAULT_MAX_AGE_SECONDS, SESSION_KEY, StepUpAuth
from craft.http.session import CookieSessionStore

KEY = "test-application-key"


@pytest.fixture
def session():
    return CookieSessionStore(KEY).load(None)


class TestStepUpAuth:
    def test_a_session_never_stamped_is_not_fresh(self, session):
        assert StepUpAuth.is_fresh(session) is False

    def test_confirm_stamps_the_current_time(self, session):
        StepUpAuth.confirm(session)
        assert session.get(SESSION_KEY) is not None
        assert StepUpAuth.age_seconds(session) < 1

    def test_a_freshly_confirmed_session_is_fresh(self, session):
        StepUpAuth.confirm(session)
        assert StepUpAuth.is_fresh(session) is True

    def test_a_session_older_than_the_window_is_not_fresh(self, session):
        session.put(SESSION_KEY, time.time() - 400)
        assert StepUpAuth.is_fresh(session, max_age_seconds=300) is False

    def test_a_session_within_the_window_is_fresh(self, session):
        session.put(SESSION_KEY, time.time() - 100)
        assert StepUpAuth.is_fresh(session, max_age_seconds=300) is True

    def test_none_session_is_never_fresh(self):
        assert StepUpAuth.is_fresh(None) is False
        assert StepUpAuth.age_seconds(None) is None

    def test_a_corrupted_timestamp_is_not_fresh(self, session):
        session.put(SESSION_KEY, "not-a-number")
        assert StepUpAuth.is_fresh(session) is False

    def test_default_window_is_used_when_not_specified(self, session):
        session.put(SESSION_KEY, time.time() - (DEFAULT_MAX_AGE_SECONDS + 10))
        assert StepUpAuth.is_fresh(session) is False
        session.put(SESSION_KEY, time.time() - (DEFAULT_MAX_AGE_SECONDS - 10))
        assert StepUpAuth.is_fresh(session) is True


class TestLoginStampsFreshness:
    def test_login_stamps_authenticated_at(self, migrated_database):
        from craft.auth.manager import AuthManager
        from craft.orm.model import Model

        class _User(Model):
            __table__ = "users"
            fillable = ["name", "email", "password"]

        manager = AuthManager(migrated_database)
        manager.logout()
        manager._session = CookieSessionStore(KEY).load(None)

        user = _User.create({"name": "Step Up Test", "email": "stepup-test@example.com", "password": "hashed"})
        manager.login(user)

        assert StepUpAuth.is_fresh(manager._current_session()) is True


class TestRequireFreshAuthMiddleware:
    def _request_with_session(self, session):
        class _Request:
            @staticmethod
            def has_session():
                return True

            @staticmethod
            def session():
                return session

            @staticmethod
            def expects_json():
                return True

        return _Request()

    def test_a_fresh_session_passes_through(self):
        from craft.http.middleware import RequireFreshAuth

        session = CookieSessionStore(KEY).load(None)
        StepUpAuth.confirm(session)
        middleware = RequireFreshAuth()
        request = self._request_with_session(session)

        assert middleware.handle(request, lambda req: "ok") == "ok"

    def test_a_stale_session_is_rejected(self):
        from craft.exceptions.handler import AuthorizationException
        from craft.http.middleware import RequireFreshAuth

        session = CookieSessionStore(KEY).load(None)
        session.put(SESSION_KEY, time.time() - 1000)
        middleware = RequireFreshAuth()
        request = self._request_with_session(session)

        with pytest.raises(AuthorizationException):
            middleware.handle(request, lambda req: "never reached")

    def test_the_max_age_parameter_from_the_route_alias_is_honoured(self):
        from craft.http.middleware import RequireFreshAuth

        session = CookieSessionStore(KEY).load(None)
        session.put(SESSION_KEY, time.time() - 100)
        # "60" simulates the string param resolve_route_middleware passes
        # from a "fresh:60" route alias.
        middleware = RequireFreshAuth("60")
        request = self._request_with_session(session)

        from craft.exceptions.handler import AuthorizationException

        with pytest.raises(AuthorizationException):
            middleware.handle(request, lambda req: "never reached")

    def test_fresh_alias_resolves_to_require_fresh_auth(self, migrated_database):
        from craft.http.kernel import Kernel

        kernel = Kernel(migrated_database)
        resolved = kernel.resolve_route_middleware(["fresh:120"])
        assert len(resolved) == 1
        assert resolved[0].max_age_seconds == 120

    def test_bare_fresh_alias_uses_the_default_window(self, migrated_database):
        from craft.http.kernel import Kernel

        kernel = Kernel(migrated_database)
        resolved = kernel.resolve_route_middleware(["fresh"])
        assert resolved[0].max_age_seconds == DEFAULT_MAX_AGE_SECONDS
