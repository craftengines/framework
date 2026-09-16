"""Sensitive-value redaction for logs and error responses.

A password, token, or credit-card number logged once is logged forever — into
every log aggregator, every backup, every engineer's terminal scrollback that
happened to be open. This scrubs known-sensitive field names recursively from
any structure bound for a log line or an error payload, and pattern-matches a
handful of secret shapes (bearer tokens, card numbers) inside free-text
messages, where a field name is not available to key off.

Category: Core Framework (Support).
Relations:
  - Applied by `JsonFormatter` (`engine/support/logging.py`) to every log
    record's payload before serialization.
  - Applied by `ExceptionHandler` (`engine/exceptions/handler.py`) to the
    logged exception context (never to what reaches the client — that path
    already only carries `code`/`message_key`, per Slice 0).
References:
  - Guide: `documentation/security.md#log-redaction`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import re
from typing import Any

REDACTED = "[REDACTED]"

#: Field names redacted case-insensitively, wherever they appear in a nested
#: structure. Substring-matched on purpose (`old_password`, `x-api-key`,
#: `stripe_secret_key` all contain one of these) rather than exact-matched,
#: since a field name a caller invents is not predictable in advance.
_SENSITIVE_KEY_FRAGMENTS = (
    "password", "passwd", "secret", "token", "api_key", "apikey",
    "authorization", "auth_token", "credit_card", "card_number", "cvv",
    "cvc", "ssn", "social_security", "private_key", "access_key",
)

#: Free-text patterns redacted inside a message string, where there is no
#: field name to key off. Each pair is (compiled pattern, replacement).
_MESSAGE_PATTERNS = (
    # `Authorization: Bearer <token>` / `Bearer <token>` on its own.
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9\-._~+/]+=*"), f"Bearer {REDACTED}"),
    # `key=value` / `key: value` where the key looks sensitive.
    (
        re.compile(
            r"(?i)\b(" + "|".join(_SENSITIVE_KEY_FRAGMENTS) + r")\w*\s*[:=]\s*"
            r"[^\s,;&]+"
        ),
        lambda m: f"{m.group(1)}={REDACTED}",
    ),
    # A run of 13-19 digits (with optional spaces/dashes every 4) — the shape
    # of a payment card number (Luhn-length range per ISO/IEC 7812).
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), REDACTED),
)


def _key_is_sensitive(key: str) -> bool:
    lowered = key.lower()
    return any(fragment in lowered for fragment in _SENSITIVE_KEY_FRAGMENTS)


def redact_message(message: str) -> str:
    """Scrub known secret shapes from a free-text string.

    Args:
        message: The text to scrub (a log message, an exception's `str()`).

    Returns:
        The message with matched spans replaced by `[REDACTED]`.
    """
    if not isinstance(message, str) or not message:
        return message
    result = message
    for pattern, replacement in _MESSAGE_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def redact_structure(value: Any, *, _depth: int = 0) -> Any:
    """Recursively redact sensitive keys from a dict/list/tuple structure.

    Args:
        value: The structure to scrub — typically a log record's `extra`
            payload or a structured error context.
        _depth: Internal recursion guard; not for callers to set.

    Returns:
        A new structure with sensitive values replaced by `[REDACTED]`. Never
        mutates the input, so a caller's own reference stays intact.
    """
    if _depth > 10:  # A pathological or cyclic structure stops here, not the log line.
        return REDACTED
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if _key_is_sensitive(str(key)) and not isinstance(item, (dict, list, tuple)):
                # A leaf value under a sensitive key name is redacted outright.
                # A container (a "tokens" list of {"token": ...} objects, say)
                # recurses instead, so the per-item field names still apply.
                result[key] = REDACTED
            else:
                result[key] = redact_structure(item, _depth=_depth + 1)
        return result
    if isinstance(value, (list, tuple)):
        redacted = [redact_structure(item, _depth=_depth + 1) for item in value]
        return type(value)(redacted) if isinstance(value, tuple) else redacted
    if isinstance(value, str):
        return redact_message(value)
    return value


__all__ = ["redact_message", "redact_structure", "REDACTED"]
