"""Context-bound signed tokens: purpose separation, context binding, expiry."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import base64
import time

import pytest

from craft.auth.signer import InvalidTokenError, Signer, SignerKeyMissingError

KEY_A = "base64:" + base64.urlsafe_b64encode(b"A" * 32).decode()
KEY_B = "base64:" + base64.urlsafe_b64encode(b"B" * 32).decode()


def test_a_token_round_trips_the_payload():
    signer = Signer(app_key=KEY_A)
    token = signer.sign("user-42", purpose="password_reset")
    assert signer.unsign(token, purpose="password_reset") == "user-42"


def test_a_token_signed_for_one_purpose_fails_another():
    signer = Signer(app_key=KEY_A)
    token = signer.sign("user-42", purpose="password_reset")
    with pytest.raises(InvalidTokenError):
        signer.unsign(token, purpose="email_verification")


def test_a_token_bound_to_one_context_fails_a_different_context():
    signer = Signer(app_key=KEY_A)
    token = signer.sign("user-42", purpose="password_reset", context="203.0.113.5")
    with pytest.raises(InvalidTokenError):
        signer.unsign(token, purpose="password_reset", context="198.51.100.9")


def test_a_token_bound_to_a_context_verifies_under_the_same_context():
    signer = Signer(app_key=KEY_A)
    token = signer.sign("user-42", purpose="password_reset", context="203.0.113.5")
    assert signer.unsign(token, purpose="password_reset", context="203.0.113.5") == "user-42"


def test_a_token_from_a_different_key_fails():
    token = Signer(app_key=KEY_A).sign("user-42", purpose="password_reset")
    with pytest.raises(InvalidTokenError):
        Signer(app_key=KEY_B).unsign(token, purpose="password_reset")


def test_an_expired_token_fails():
    signer = Signer(app_key=KEY_A)
    token = signer.sign("user-42", purpose="password_reset", ttl_seconds=-1)
    with pytest.raises(InvalidTokenError):
        signer.unsign(token, purpose="password_reset")


def test_a_token_with_no_ttl_never_expires():
    signer = Signer(app_key=KEY_A)
    token = signer.sign("user-42", purpose="password_reset")
    time.sleep(0.01)
    assert signer.unsign(token, purpose="password_reset") == "user-42"


def test_a_malformed_token_fails():
    with pytest.raises(InvalidTokenError):
        Signer(app_key=KEY_A).unsign("not-a-real-token", purpose="password_reset")


def test_an_empty_key_raises_signer_key_missing():
    with pytest.raises(SignerKeyMissingError):
        Signer(app_key="")


def test_facade_resolves_from_the_container_configured_app_key(migrated_database):
    from craft.facades import Signer as SignerFacade

    config = migrated_database.make("config")
    original = config.get("app.APP_KEY")
    config.set("app.APP_KEY", KEY_A)
    try:
        token = SignerFacade.sign("via-facade", purpose="test")
        assert SignerFacade.unsign(token, purpose="test") == "via-facade"
    finally:
        config.set("app.APP_KEY", original)
