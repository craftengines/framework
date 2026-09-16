"""Step-up authentication — require a *recent* login for a sensitive action.

An ordinary session lasting hours is right for browsing; it is wrong for
changing a password, viewing billing details, or granting another user
admin access. Step-up auth checks not just "is someone logged in" but "did
they authenticate recently enough for *this*" — the same idea as sudo's
timestamp file, applied to a web session.

Category: Core Framework (Auth).
Relations:
  - `AuthManager._remember_in_session()` (`engine/auth/manager.py`) stamps
    `authenticated_at` on every login; this module reads and refreshes it.
  - `RequireFreshAuth` (`engine/http/middleware.py`), route middleware alias
    `fresh:<seconds>` — see `Kernel.route_middleware_aliases`.
References:
  - Guide: `documentation/security.md#step-up-auth`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import time
from typing import Any, Optional

#: The session key `AuthManager` stamps on every login.
SESSION_KEY = "authenticated_at"

#: Default freshness window for a `fresh` alias with no explicit parameter.
DEFAULT_MAX_AGE_SECONDS = 300


class StepUpAuth:
    """Reads and refreshes the session's authentication freshness timestamp."""

    @staticmethod
    def confirm(session: Any) -> None:
        """Stamp the session as freshly authenticated, right now.

        Call this after a step-up re-authentication prompt succeeds (the
        user re-entered their password), not only at the original login —
        that is what lets a stale session become fresh again without a full
        logout/login cycle.
        """
        if session is not None:
            session.put(SESSION_KEY, time.time())

    @staticmethod
    def age_seconds(session: Any) -> Optional[float]:
        """Seconds since the session was last (re-)authenticated, or `None`
        if it was never stamped (a session predating this feature)."""
        if session is None:
            return None
        stamped = session.get(SESSION_KEY)
        if stamped is None:
            return None
        try:
            return time.time() - float(stamped)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def is_fresh(session: Any, max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS) -> bool:
        """Whether the session's authentication is within the freshness window.

        A session never stamped (predates this feature, or was rehydrated
        from a store written before it existed) is NOT fresh — fail closed:
        an unknown age must not be treated as "just authenticated."
        """
        age = StepUpAuth.age_seconds(session)
        return age is not None and age <= max_age_seconds


__all__ = ["StepUpAuth", "SESSION_KEY", "DEFAULT_MAX_AGE_SECONDS"]
