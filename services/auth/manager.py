"""Authentication manager for Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import importlib
from typing import Any, Dict, Optional

from services.auth.password import Hash


class AuthManager:
    """Resolves, authenticates and remembers the current user."""

    def __init__(self, app: Any = None):
        self.app = app
        self._user: Optional[Any] = None

    # -- provider resolution ---------------------------------------------------

    def _config(self) -> Any:
        if self.app is None:
            return None
        try:
            return self.app.make("config")
        except Exception:
            return None

    def user_model(self) -> Any:
        """Resolve the configured user model class."""
        config = self._config()
        path = (
            config.get("auth.providers.users.model") if config else None
        ) or "app.Models.User.User"
        module_path, _, class_name = path.rpartition(".")
        return getattr(importlib.import_module(module_path), class_name)

    # -- state -----------------------------------------------------------------

    def user(self) -> Optional[Any]:
        return self._user

    def id(self) -> Any:
        return self._user.get_attribute("id") if self._user is not None else None

    def check(self) -> bool:
        return self._user is not None

    def guest(self) -> bool:
        return self._user is None

    def login(self, user: Any) -> Any:
        """Authenticate a user and persist them into the session."""
        self._user = user
        self._remember_in_session(user)
        return user

    def login_using_id(self, user_id: Any) -> Optional[Any]:
        user = self.user_model().find(user_id)
        return self.login(user) if user is not None else None

    def set_user(self, user: Any) -> Any:
        """Set the user for this request only, without touching the session.

        Used when rehydrating from an existing session — writing back would
        rotate the session id on every request.
        """
        self._user = user
        return user

    def reset(self) -> None:
        """Clear in-request state without logging the user out of the session.

        The manager is a singleton, so a user resolved on one request must not
        leak into the next; but clearing memory is not the same as ending the
        session, which is what `logout()` does.
        """
        self._user = None

    def logout(self) -> None:
        """End the session — clears memory and forgets the stored user."""
        self._user = None
        self._forget_session()

    # -- session persistence ---------------------------------------------------

    def set_session(self, session: Any) -> None:
        """Bind the current request's session so logins survive redirects."""
        self._session = session

    def _current_session(self) -> Any:
        return getattr(self, "_session", None)

    def _session_key(self) -> str:
        from services.http.middleware import Authenticate

        return Authenticate.SESSION_KEY

    def _remember_in_session(self, user: Any) -> None:
        session = self._current_session()
        if session is None or user is None:
            return
        # Rotate the id on login — otherwise a session fixed before login stays
        # valid afterwards (session fixation).
        session.regenerate()
        session.put(self._session_key(), user.get_attribute(self.primary_key_name()))

    def _forget_session(self) -> None:
        session = self._current_session()
        if session is not None:
            session.forget(self._session_key())

    def primary_key_name(self) -> str:
        return getattr(self.user_model(), "primary_key", "id")

    # -- authentication --------------------------------------------------------

    def validate(self, credentials: Dict[str, Any]) -> Optional[Any]:
        """Verify credentials without logging the user in."""
        credentials = dict(credentials or {})
        password = credentials.pop("password", None)
        if not credentials or password is None:
            return None

        query = self.user_model().query()
        for column, value in credentials.items():
            query = query.where(column, value)
        user = query.first()

        if user is None:
            # Compare against a dummy hash so a missing user costs the same as a
            # wrong password — otherwise timing reveals which emails exist.
            Hash.check(str(password), Hash.make("timing-equalizer"))
            return None

        if not Hash.check(str(password), user.get_attribute("password")):
            return None
        return user

    def attempt(self, credentials: Dict[str, Any]) -> bool:
        """Validate credentials and log the user in on success."""
        user = self.validate(credentials)
        if user is None:
            return False
        self.login(user)
        return True

    def once(self, credentials: Dict[str, Any]) -> bool:
        """Authenticate for a single request without persisting state."""
        return self.validate(credentials) is not None

    # -- authorization helpers -------------------------------------------------

    def has_permission(self, slug: str) -> bool:
        if self._user is None:
            return False
        return bool(self._user.has_permission(slug))

    def is_admin(self) -> bool:
        if self._user is None:
            return False
        return bool(self._user.get_attribute("is_admin"))


__all__ = ["AuthManager", "Hash"]
