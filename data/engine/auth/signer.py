"""Context-bound signed tokens — for password resets, email verification,
one-time links, and anything else that must not be replayable outside the
purpose and context it was minted for.

A signature alone only proves the token was not tampered with; it says
nothing about *where* it may be redeemed. Binding `purpose` (so a password-
reset token cannot double as an email-verification token) and `context`
(typically the requesting IP, user agent, or session id — so a token leaked
in a referrer header or a shared inbox cannot be redeemed from a different
browser) closes the replay gap a bare HMAC leaves open.

Category: Core Framework (Auth).
Relations:
  - Bound as `signer`, exposed via the `Signer` facade.
  - Derives its key from `app.APP_KEY` via HMAC, domain-separated per
    `purpose` — one leaked purpose-key must not forge tokens for another
    purpose, the same reasoning as `engine/security/vault.py`'s HKDF label.
References:
  - Guide: `documentation/security.md#context-bound-tokens`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Optional


class SignerKeyMissingError(RuntimeError):
    """No usable `APP_KEY` is configured."""

    code = "SIGNER_KEY_MISSING"
    message_key = "security.signer.key_missing"


class InvalidTokenError(RuntimeError):
    """A token failed to verify: bad signature, wrong purpose/context, or expired."""

    code = "SIGNER_TOKEN_INVALID"
    message_key = "security.signer.token_invalid"


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


class Signer:
    """Mints and verifies purpose- and context-bound signed tokens."""

    def __init__(self, app_key: Optional[str] = None) -> None:
        """Build a signer bound to one master key.

        Args:
            app_key: The raw `APP_KEY` value. Reads `app.APP_KEY` from the
                container when omitted.

        Raises:
            SignerKeyMissingError: No key is available from either source.
        """
        if app_key is None:
            app_key = self._app_key_from_container()
        if not app_key:
            raise SignerKeyMissingError(
                "APP_KEY is empty — the signer has no key to derive from. "
                "Run `python dev.py key:generate` first."
            )
        self._app_key = app_key.encode("utf-8")

    @staticmethod
    def _app_key_from_container() -> str:
        try:
            from engine.container.application import Container

            config = Container.getInstance().make("config")
            return str(config.get("app.APP_KEY", "") or "")
        except Exception:
            return ""

    def _purpose_key(self, purpose: str) -> bytes:
        """Derive a purpose-specific key via HMAC, so one purpose's key
        cannot be used to forge a token for another."""
        return hmac.new(self._app_key, purpose.encode("utf-8"), hashlib.sha256).digest()

    def sign(
        self,
        payload: str,
        *,
        purpose: str,
        context: str = "",
        ttl_seconds: Optional[int] = None,
    ) -> str:
        """Mint a signed token.

        Args:
            payload: The value to protect (a user id, an email address...).
            purpose: What this token is for (`"password_reset"`,
                `"email_verification"`) — a token minted for one purpose
                verifies only against the same purpose.
            context: What this token is bound to (an IP, a user agent, a
                session id). Empty by default — pass it to make the token
                unusable outside where it was issued.
            ttl_seconds: Seconds until expiry, or `None` for no expiry.

        Returns:
            An opaque, URL-safe token.
        """
        expires_at = int(time.time()) + ttl_seconds if ttl_seconds is not None else None
        body = json.dumps(
            {"p": payload, "c": context, "e": expires_at}, separators=(",", ":")
        ).encode("utf-8")
        body_b64 = _b64encode(body)
        signature = _b64encode(hmac.new(self._purpose_key(purpose), body_b64.encode("ascii"), hashlib.sha256).digest())
        return f"{body_b64}.{signature}"

    def unsign(self, token: str, *, purpose: str, context: str = "") -> str:
        """Verify a token and return its payload.

        Args:
            token: A value previously returned by `sign()`.
            purpose: Must match the purpose the token was signed for.
            context: Must match the context the token was signed for.

        Returns:
            The original payload.

        Raises:
            InvalidTokenError: Bad signature, wrong purpose, wrong context,
                or the token has expired.
        """
        try:
            body_b64, signature = token.split(".", 1)
        except ValueError:
            raise InvalidTokenError(f"{InvalidTokenError.code}: malformed token")

        expected = _b64encode(hmac.new(self._purpose_key(purpose), body_b64.encode("ascii"), hashlib.sha256).digest())
        if not hmac.compare_digest(expected, signature):
            raise InvalidTokenError(f"{InvalidTokenError.code}: signature mismatch")

        try:
            data: dict[str, Any] = json.loads(_b64decode(body_b64))
        except (ValueError, UnicodeDecodeError):
            raise InvalidTokenError(f"{InvalidTokenError.code}: malformed payload")

        if data.get("c", "") != context:
            raise InvalidTokenError(f"{InvalidTokenError.code}: context mismatch")

        expires_at = data.get("e")
        if expires_at is not None and time.time() > expires_at:
            raise InvalidTokenError(f"{InvalidTokenError.code}: expired")

        return str(data.get("p", ""))


__all__ = ["Signer", "SignerKeyMissingError", "InvalidTokenError"]
