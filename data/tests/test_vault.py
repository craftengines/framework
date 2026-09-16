"""Credential vault: AES-256-GCM round-trip, key separation, tamper detection."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import base64

import pytest

from craft.security.vault import Vault, VaultDecryptionError, VaultKeyMissingError

KEY_A = "base64:" + base64.urlsafe_b64encode(b"A" * 32).decode()
KEY_B = "base64:" + base64.urlsafe_b64encode(b"B" * 32).decode()


def test_a_token_decrypts_back_to_the_original_plaintext():
    vault = Vault(app_key=KEY_A)
    token = vault.encrypt("super-secret-api-key")
    assert vault.decrypt(token) == "super-secret-api-key"


def test_the_token_never_contains_the_plaintext():
    vault = Vault(app_key=KEY_A)
    token = vault.encrypt("super-secret-api-key")
    assert "super-secret-api-key" not in token


def test_encrypting_the_same_plaintext_twice_yields_different_tokens():
    """A random nonce per call - AES-GCM breaks under nonce reuse."""
    vault = Vault(app_key=KEY_A)
    assert vault.encrypt("same-value") != vault.encrypt("same-value")


def test_a_token_from_a_different_key_fails_to_decrypt():
    token = Vault(app_key=KEY_A).encrypt("secret")
    with pytest.raises(VaultDecryptionError):
        Vault(app_key=KEY_B).decrypt(token)


def test_a_tampered_token_fails_to_decrypt():
    """The GCM authentication tag catches bit-flipping, not just wrong keys."""
    vault = Vault(app_key=KEY_A)
    token = vault.encrypt("secret")
    tampered = token[:-4] + ("A" if token[-4] != "A" else "B") + token[-3:]
    with pytest.raises(VaultDecryptionError):
        vault.decrypt(tampered)


def test_a_non_vault_string_fails_to_decrypt():
    with pytest.raises(VaultDecryptionError):
        Vault(app_key=KEY_A).decrypt("not-a-vault-token")


def test_an_empty_key_raises_vault_key_missing():
    with pytest.raises(VaultKeyMissingError):
        Vault(app_key="")


def test_is_vault_token_distinguishes_sealed_from_plain_values():
    vault = Vault(app_key=KEY_A)
    assert vault.is_vault_token(vault.encrypt("x")) is True
    assert vault.is_vault_token("plain-value") is False
    assert vault.is_vault_token(None) is False


def test_facade_resolves_from_the_container_configured_app_key(migrated_database):
    from craft.facades import Vault as VaultFacade

    config = migrated_database.make("config")
    original = config.get("app.APP_KEY")
    config.set("app.APP_KEY", KEY_A)
    try:
        token = VaultFacade.encrypt("via-facade")
        assert VaultFacade.decrypt(token) == "via-facade"
    finally:
        config.set("app.APP_KEY", original)
