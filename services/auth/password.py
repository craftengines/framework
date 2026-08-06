"""Password hashing for Codepy Framework.

Uses bcrypt via passlib when available and falls back to PBKDF2-HMAC-SHA256
from the standard library, so a fresh install never silently stores plaintext.
"""
# Codepy Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from typing import Optional

_PBKDF2_ROUNDS = 260_000
_PBKDF2_PREFIX = "pbkdf2_sha256"


def _passlib_context():
    """Return a working bcrypt context, or None to use the PBKDF2 fallback.

    passlib only loads its bcrypt backend lazily, and that load fails against
    bcrypt 4.x (`module 'bcrypt' has no attribute '__about__'`). Constructing
    the context is therefore not proof it works — probe it with a real hash.
    """
    try:
        from passlib.context import CryptContext
    except ImportError:
        return None

    import logging

    # passlib logs the backend traceback at ERROR before raising; the fallback
    # is deliberate, so don't spam every command with it.
    passlib_logger = logging.getLogger("passlib")
    previous_level = passlib_logger.level
    passlib_logger.setLevel(logging.CRITICAL)
    try:
        context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        probe = context.hash("codepy-backend-probe")
        if not context.verify("codepy-backend-probe", probe):
            return None
        return context
    except Exception:
        return None
    finally:
        passlib_logger.setLevel(previous_level)


_CONTEXT = _passlib_context()


class Hash:
    """Static password hashing API (`Hash.make`, `Hash.check`)."""

    @staticmethod
    def make(password: str, rounds: Optional[int] = None) -> str:
        if not isinstance(password, str):
            password = str(password)

        if _CONTEXT is not None:
            return _CONTEXT.hash(password)

        salt = secrets.token_bytes(16)
        iterations = rounds or _PBKDF2_ROUNDS
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return "$".join(
            [
                _PBKDF2_PREFIX,
                str(iterations),
                base64.b64encode(salt).decode("ascii"),
                base64.b64encode(digest).decode("ascii"),
            ]
        )

    @staticmethod
    def check(password: str, hashed: Optional[str]) -> bool:
        if not hashed or not isinstance(hashed, str):
            return False

        if hashed.startswith(_PBKDF2_PREFIX + "$"):
            try:
                _, iterations, salt_b64, digest_b64 = hashed.split("$", 3)
                salt = base64.b64decode(salt_b64)
                expected = base64.b64decode(digest_b64)
            except (ValueError, TypeError):
                return False
            candidate = hashlib.pbkdf2_hmac(
                "sha256", str(password).encode("utf-8"), salt, int(iterations)
            )
            return hmac.compare_digest(candidate, expected)

        if _CONTEXT is not None:
            try:
                return _CONTEXT.verify(str(password), hashed)
            except Exception:
                return False

        return False

    @staticmethod
    def needs_rehash(hashed: Optional[str]) -> bool:
        """True when a stored hash predates the current algorithm."""
        if not hashed:
            return True
        if _CONTEXT is not None:
            if hashed.startswith(_PBKDF2_PREFIX + "$"):
                return True
            try:
                return _CONTEXT.needs_update(hashed)
            except Exception:
                return True
        return not hashed.startswith(_PBKDF2_PREFIX + "$")

    @staticmethod
    def is_hashed(value: Optional[str]) -> bool:
        """Detect whether a value is already a hash rather than plaintext."""
        if not value or not isinstance(value, str):
            return False
        return value.startswith((_PBKDF2_PREFIX + "$", "$2a$", "$2b$", "$2y$", "$argon2"))


__all__ = ["Hash"]
