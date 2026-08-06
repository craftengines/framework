"""Middleware for Codepy Framework.

Middleware is synchronous: `handle(request, next_callable)` returns a response.
The kernel composes the stack in registration order, so `StartSession` must come
first — `VerifyCsrfToken` and `Authenticate` both read from the session.
"""

from __future__ import annotations

import fnmatch
import secrets
from typing import Any, Callable, List, Optional


class Middleware:
    """Base middleware — pass the request through untouched."""

    def handle(self, request: Any, next_callable: Callable) -> Any:
        return next_callable(request)


def _container(app: Any = None) -> Any:
    if app is not None:
        return app
    from services.container.application import Container

    return Container.getInstance()


def _as_starlette(response: Any) -> Any:
    """Normalise a framework response into a Starlette response, if possible."""
    from starlette.responses import Response as StarletteResponse

    if isinstance(response, StarletteResponse):
        return response
    if hasattr(response, "to_starlette"):
        return response.to_starlette()
    return None


class StartSession(Middleware):
    """Load the session before the request, persist it after."""

    COOKIE_NAME = "codepy_session"

    def __init__(self, app: Any = None):
        self.app = app
        self._store = None

    def store(self) -> Any:
        if self._store is None:
            from services.http.session import make_store

            self._store = make_store(_container(self.app))
        return self._store

    def _config(self, key: str, default: Any) -> Any:
        try:
            return _container(self.app).make("config").get(key, default)
        except Exception:
            return default

    def handle(self, request: Any, next_callable: Callable) -> Any:
        from services.http.session import current_session

        store = self.store()
        cookie_name = self._config("session.cookie", self.COOKIE_NAME)

        session = store.load(request.cookies.get(cookie_name))
        request.state.session = session
        # Publish it so view helpers (`@csrf`) can reach it without the request.
        token = current_session.set(session)

        try:
            response = next_callable(request)
        finally:
            current_session.reset(token)

        value = store.save(request.state.session)
        starlette_response = _as_starlette(response)
        if starlette_response is None:
            return response

        starlette_response.set_cookie(
            cookie_name,
            value,
            max_age=int(self._config("session.lifetime", 7200)),
            httponly=True,
            samesite=self._config("session.same_site", "lax"),
            secure=bool(self._config("session.secure", False)),
            path="/",
        )
        return starlette_response


class VerifyCsrfToken(Middleware):
    """Reject state-changing requests that carry no valid CSRF token."""

    #: Methods that are safe by definition and never checked.
    READ_METHODS = ("GET", "HEAD", "OPTIONS", "TRACE")

    #: URI patterns exempt from verification (fnmatch syntax).
    except_paths: List[str] = ["api/*"]

    def __init__(self, app: Any = None, except_paths: Optional[List[str]] = None):
        self.app = app
        if except_paths is not None:
            self.except_paths = list(except_paths)

    def _enabled(self) -> bool:
        try:
            return bool(_container(self.app).make("config").get("session.csrf", True))
        except Exception:
            return True

    def is_exempt(self, path: str) -> bool:
        normalised = path.lstrip("/")
        return any(
            fnmatch.fnmatch(normalised, pattern.lstrip("/")) for pattern in self.except_paths
        )

    def token_from(self, request: Any) -> Optional[str]:
        header = request.headers.get("x-csrf-token") or request.headers.get("x-xsrf-token")
        if header:
            return header
        if hasattr(request, "input"):
            return request.input("_token")
        return None

    def handle(self, request: Any, next_callable: Callable) -> Any:
        if (
            request.method.upper() in self.READ_METHODS
            or not self._enabled()
            or self.is_exempt(request.url.path)
            or not getattr(request, "has_session", lambda: False)()
        ):
            return next_callable(request)

        expected = request.session().token()
        provided = self.token_from(request) or ""

        if not secrets.compare_digest(str(expected), str(provided)):
            from services.exceptions.handler import CodepyException

            error = CodepyException("CSRF token mismatch.")
            error.status_code = 419  # Laravel's "page expired"
            raise error

        return next_callable(request)


class Authenticate(Middleware):
    """Resolve the session's user onto the auth manager."""

    SESSION_KEY = "auth_user_id"

    def __init__(self, app: Any = None):
        self.app = app

    def handle(self, request: Any, next_callable: Callable) -> Any:
        auth = _container(self.app).make("auth")

        # The auth manager is a singleton, so a user resolved on a previous
        # request must not leak into this one. `reset()` clears memory without
        # ending the session — `logout()` here would erase the very key we are
        # about to read.
        auth.reset()

        if getattr(request, "has_session", lambda: False)():
            session = request.session()
            auth.set_session(session)
            user_id = session.get(self.SESSION_KEY)
            if user_id is not None:
                user = auth.user_model().find(user_id)
                if user is None:
                    # The user was deleted while the session lived on.
                    session.forget(self.SESSION_KEY)
                else:
                    auth.set_user(user)
        else:
            auth.set_session(None)

        return next_callable(request)


class RequireAuth(Middleware):
    """Terminate the request when nobody is authenticated."""

    def __init__(self, app: Any = None, redirect_to: str = "/login"):
        self.app = app
        self.redirect_to = redirect_to

    def handle(self, request: Any, next_callable: Callable) -> Any:
        if _container(self.app).make("auth").check():
            return next_callable(request)

        if getattr(request, "expects_json", lambda: False)():
            from services.exceptions.handler import AuthorizationException

            raise AuthorizationException("Unauthenticated.")

        from starlette.responses import RedirectResponse

        return RedirectResponse(self.redirect_to, status_code=302)


class AuthenticateApiToken(Middleware):
    """Authenticate via `Authorization: Bearer <token>` for the api guard."""

    def __init__(self, app: Any = None, column: Optional[str] = None):
        self.app = app
        self.column = column

    def handle(self, request: Any, next_callable: Callable) -> Any:
        app = _container(self.app)
        auth = app.make("auth")
        auth.logout()

        token = getattr(request, "bearer_token", lambda: None)()
        if token:
            try:
                column = self.column or app.make("config").get(
                    "auth.guards.api.token_name", "api_token"
                )
            except Exception:
                column = self.column or "api_token"
            user = auth.user_model().query().where(column, token).first()
            if user is not None:
                auth.login(user)

        return next_callable(request)


__all__ = [
    "Middleware",
    "StartSession",
    "VerifyCsrfToken",
    "Authenticate",
    "RequireAuth",
    "AuthenticateApiToken",
]
