"""TOTP: verified against the official RFC 6238 test vectors, plus our own
verify_code() window/format behaviour.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest

from craft.auth.totp import generate_code, generate_secret, provisioning_uri, verify_code

# RFC 6238 Appendix B's shared SHA-1 test secret, "12345678901234567890"
# (ASCII), base32-encoded — the vectors below are the standard's own.
RFC_6238_SECRET = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"

RFC_6238_VECTORS = [
    (59, "94287082"),
    (1111111109, "07081804"),
    (1111111111, "14050471"),
    (1234567890, "89005924"),
    (2000000000, "69279037"),
]


@pytest.mark.parametrize("timestamp,expected", RFC_6238_VECTORS)
def test_matches_the_official_rfc_6238_test_vectors(timestamp, expected):
    assert generate_code(RFC_6238_SECRET, at=timestamp, digits=8) == expected


def test_generate_secret_returns_a_valid_base32_string():
    import base64

    secret = generate_secret()
    # Must decode cleanly (raises on invalid base32).
    base64.b32decode(secret + "=" * (-len(secret) % 8))


def test_generate_secret_is_random_each_time():
    assert generate_secret() != generate_secret()


def test_verify_code_accepts_the_current_code():
    secret = generate_secret()
    code = generate_code(secret, at=1_700_000_000)
    assert verify_code(secret, code, at=1_700_000_000) is True


def test_verify_code_rejects_a_wrong_code():
    secret = generate_secret()
    assert verify_code(secret, "000000", at=1_700_000_000) is False


def test_verify_code_tolerates_one_step_of_clock_drift():
    secret = generate_secret()
    code = generate_code(secret, at=1_700_000_000)
    # One period (30s) later, still within window=1.
    assert verify_code(secret, code, at=1_700_000_000 + 30) is True


def test_verify_code_rejects_drift_beyond_the_window():
    secret = generate_secret()
    code = generate_code(secret, at=1_700_000_000)
    # Three periods later, outside the default window=1.
    assert verify_code(secret, code, at=1_700_000_000 + 90) is False


def test_verify_code_rejects_non_numeric_input():
    secret = generate_secret()
    assert verify_code(secret, "abcdef") is False


def test_verify_code_rejects_an_invalid_secret():
    assert verify_code("not-valid-base32!!!", "123456") is False


def test_provisioning_uri_has_the_expected_shape():
    uri = provisioning_uri(RFC_6238_SECRET, account_name="user@example.com", issuer="Craft")
    assert uri.startswith("otpauth://totp/")
    assert f"secret={RFC_6238_SECRET}" in uri
    assert "issuer=Craft" in uri
