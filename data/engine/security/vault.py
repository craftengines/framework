"""Credential vault — AES-256-GCM encryption at rest for stored secrets.

Encrypts values a tenant or the operator must store (a third-party API key,
an OAuth client secret) so a database dump does not hand them out in
plaintext. Never a hand-rolled cipher: `cryptography` (pyca), the maintained,
audited binding to OpenSSL, does the actual AES-GCM.

The encryption key is derived from `APP_KEY` via HKDF-SHA256 with a
domain-separation label distinct from every other use of `APP_KEY` (session
signing, CSRF tokens) — reusing one master key across unrelated primitives is
the kind of shortcut that turns a bug in one into a break in all of them.

Category: Core Framework (Security).
Relations:
  - Bound as `vault`, exposed via the `Vault` facade.
  - Reads `app.APP_KEY`, same source and same `base64:` prefix convention as
    `engine/http/session.py`'s signing key and `dev.py key:generate`.
References:
  - Guide: `documentation/security.md#credential-vault`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import base64
import os
from typing import Any, Optional

_HKDF_INFO = b"craft.vault.v1.aes256gcm"
_NONCE_LEN = 12  # 96-bit, the size AES-GCM is designed for.
_TOKEN_PREFIX = "vault:v1:"


class VaultKeyMissingError(RuntimeError):
    """No usable `APP_KEY` is configured — the vault has nothing to derive from."""

    code = "VAULT_KEY_MISSING"
    message_key = "security.vault.key_missing"


class VaultDecryptionError(RuntimeError):
    """A token failed to decrypt: wrong key, corrupted data, or tampering.

    AES-GCM authenticates the ciphertext, so this also covers an attacker
    flipping bits — the tag check fails closed rather than returning garbage.
    """

    code = "VAULT_DECRYPTION_FAILED"
    message_key = "security.vault.decryption_failed"


def _raw_app_key(app_key: str) -> bytes:
    """Decode the `base64:...`-prefixed or raw `APP_KEY` into raw bytes."""
    if app_key.startswith("base64:"):
        return base64.urlsafe_b64decode(app_key[len("base64:"):] + "==")
    return app_key.encode("utf-8")


def _derive_key(app_key: str) -> bytes:
    """HKDF-SHA256(APP_KEY) -> a 32-byte AES-256 key, domain-separated by info."""
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF

    hkdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=_HKDF_INFO)
    return hkdf.derive(_raw_app_key(app_key))


class Vault:
    """AES-256-GCM encryption for values that must not sit in the database in
    plaintext. Construct with an explicit key for testing; in the app, resolve
    through the container so it reads `APP_KEY` from config.
    """

    def __init__(self, app_key: Optional[str] = None) -> None:
        """Build a vault bound to one key.

        Args:
            app_key: The raw `APP_KEY` value (`base64:...` or plain). Reads
                `app.APP_KEY` from the container when omitted.

        Raises:
            VaultKeyMissingError: No key is available from either source.
        """
        if app_key is None:
            app_key = self._app_key_from_container()
        if not app_key:
            raise VaultKeyMissingError(
                "APP_KEY is empty — the vault has no key to derive from. "
                "Run `python dev.py key:generate` first."
            )
        self._key = _derive_key(app_key)

    @staticmethod
    def _app_key_from_container() -> str:
        try:
            from engine.container.application import Container

            config = Container.getInstance().make("config")
            return str(config.get("app.APP_KEY", "") or "")
        except Exception:
            return ""

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string, returning a versioned, self-contained token.

        Args:
            plaintext: The value to protect.

        Returns:
            `"vault:v1:" + base64(nonce || ciphertext || tag)`. The nonce is
            random per call (AES-GCM requires a unique nonce per key; a
            colliding nonce breaks confidentiality AND authenticity), so
            encrypting the same plaintext twice yields different tokens.
        """
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        nonce = os.urandom(_NONCE_LEN)
        aesgcm = AESGCM(self._key)
        sealed = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        return _TOKEN_PREFIX + base64.urlsafe_b64encode(nonce + sealed).decode("ascii")

    def decrypt(self, token: str) -> str:
        """Reverse `encrypt()`.

        Args:
            token: A value previously returned by `encrypt()`.

        Returns:
            The original plaintext.

        Raises:
            VaultDecryptionError: The token is malformed, was sealed under a
                different key, or its authentication tag does not match
                (corruption or tampering).
        """
        if not token.startswith(_TOKEN_PREFIX):
            raise VaultDecryptionError(f"{VaultDecryptionError.code}: not a vault token")
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        try:
            raw = base64.urlsafe_b64decode(token[len(_TOKEN_PREFIX):])
            nonce, sealed = raw[:_NONCE_LEN], raw[_NONCE_LEN:]
            aesgcm = AESGCM(self._key)
            return aesgcm.decrypt(nonce, sealed, None).decode("utf-8")
        except Exception as exc:
            raise VaultDecryptionError(f"{VaultDecryptionError.code}: {exc}") from exc

    def is_vault_token(self, value: Any) -> bool:
        """Whether `value` looks like a token this vault produced (not decrypted)."""
        return isinstance(value, str) and value.startswith(_TOKEN_PREFIX)


__all__ = ["Vault", "VaultKeyMissingError", "VaultDecryptionError"]
