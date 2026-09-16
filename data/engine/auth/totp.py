"""TOTP — time-based one-time passwords (RFC 6238, built on HOTP, RFC 4226).

Pure standard library (`hmac`, `hashlib`, `struct`, `base64`, `secrets`): a
second-factor code generator is exactly the kind of small, well-specified
primitive that does not earn a new third-party dependency and its supply-
chain surface, and pulls in nothing more can go wrong.

Category: Core Framework (Auth).
Relations:
  - Not container-bound: it is a pure algorithm with no shared state, used
    directly by the application's own 2FA enrollment/verification flow (it
    has nowhere else to store a user's secret — that is app data).
References:
  - Guide: `documentation/security.md#totp`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from typing import Optional
from urllib.parse import quote

_DEFAULT_DIGITS = 6
_DEFAULT_PERIOD = 30
_DEFAULT_SECRET_BYTES = 20  # 160 bits — RFC 4226's own recommended minimum.


def generate_secret(length: int = _DEFAULT_SECRET_BYTES) -> str:
    """A new random secret, base32-encoded (the form authenticator apps expect).

    Args:
        length: Secret length in bytes before encoding.

    Returns:
        A base32 string with no padding.
    """
    return base64.b32encode(secrets.token_bytes(length)).decode("ascii").rstrip("=")


def _hotp(secret_bytes: bytes, counter: int, digits: int) -> str:
    """HOTP (RFC 4226): an HMAC-SHA1-derived code for one counter value."""
    counter_bytes = struct.pack(">Q", counter)
    digest = hmac.new(secret_bytes, counter_bytes, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    truncated = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(truncated % (10 ** digits)).zfill(digits)


def _decode_secret(secret: str) -> bytes:
    padding = "=" * (-len(secret) % 8)
    return base64.b32decode(secret.upper() + padding)


def generate_code(secret: str, *, at: Optional[int] = None, digits: int = _DEFAULT_DIGITS, period: int = _DEFAULT_PERIOD) -> str:
    """The TOTP code for a secret at a given time.

    Args:
        secret: Base32-encoded secret (as returned by `generate_secret()`).
        at: Unix timestamp to generate for; defaults to now.
        digits: Code length.
        period: Time-step in seconds.

    Returns:
        The zero-padded numeric code.
    """
    timestamp = int(at if at is not None else time.time())
    counter = timestamp // period
    return _hotp(_decode_secret(secret), counter, digits)


def verify_code(
    secret: str,
    code: str,
    *,
    at: Optional[int] = None,
    digits: int = _DEFAULT_DIGITS,
    period: int = _DEFAULT_PERIOD,
    window: int = 1,
) -> bool:
    """Verify a submitted code, tolerating clock drift within `window` steps.

    Args:
        secret: Base32-encoded secret.
        code: The code the user typed.
        at: Unix timestamp to verify against; defaults to now.
        digits: Code length.
        period: Time-step in seconds.
        window: How many steps before/after the current one to also accept -
            a TOTP app and a server clock are never perfectly synchronized.

    Returns:
        Whether `code` matches any step within the window.
    """
    if not code or not code.isdigit():
        return False
    timestamp = int(at if at is not None else time.time())
    counter = timestamp // period
    try:
        secret_bytes = _decode_secret(secret)
    except Exception:
        return False
    for offset in range(-window, window + 1):
        candidate = _hotp(secret_bytes, counter + offset, digits)
        if hmac.compare_digest(candidate, code):
            return True
    return False


def provisioning_uri(secret: str, *, account_name: str, issuer: str, digits: int = _DEFAULT_DIGITS, period: int = _DEFAULT_PERIOD) -> str:
    """An `otpauth://` URI for a QR code, per Google Authenticator's key-uri-format.

    Args:
        secret: Base32-encoded secret.
        account_name: Shown under the entry in the authenticator app
            (typically the user's email).
        issuer: Shown as the entry's label (the application's name).
        digits: Code length.
        period: Time-step in seconds.

    Returns:
        An `otpauth://totp/...` URI.
    """
    label = quote(f"{issuer}:{account_name}")
    return (
        f"otpauth://totp/{label}?secret={secret}&issuer={quote(issuer)}"
        f"&digits={digits}&period={period}&algorithm=SHA1"
    )


__all__ = ["generate_secret", "generate_code", "verify_code", "provisioning_uri"]
