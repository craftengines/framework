"""Sensitive-value redaction: known field names, message patterns, and the
JsonFormatter/TextFormatter integration that applies it to every log line.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import json
import logging

from craft.support.logging import JsonFormatter, TextFormatter
from craft.support.redaction import REDACTED, redact_message, redact_structure


def _record(message: str, **extra) -> logging.LogRecord:
    record = logging.LogRecord(
        name="craft", level=logging.INFO, pathname=__file__, lineno=1,
        msg=message, args=(), exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


class TestRedactStructure:
    def test_a_password_field_is_redacted_regardless_of_case(self):
        assert redact_structure({"Password": "hunter2"}) == {"Password": REDACTED}

    def test_a_field_containing_a_sensitive_fragment_is_redacted(self):
        assert redact_structure({"old_password": "x", "stripe_secret_key": "y"}) == {
            "old_password": REDACTED, "stripe_secret_key": REDACTED,
        }

    def test_an_ordinary_field_is_left_alone(self):
        assert redact_structure({"username": "alice"}) == {"username": "alice"}

    def test_redaction_recurses_into_nested_dicts_and_lists(self):
        value = {"user": {"name": "alice", "password": "hunter2"}, "tokens": [{"token": "abc"}]}
        result = redact_structure(value)
        assert result["user"]["password"] == REDACTED
        assert result["user"]["name"] == "alice"
        assert result["tokens"][0]["token"] == REDACTED

    def test_redaction_does_not_mutate_the_original(self):
        original = {"password": "hunter2"}
        redact_structure(original)
        assert original["password"] == "hunter2"


class TestRedactMessage:
    def test_a_bearer_token_is_redacted(self):
        result = redact_message("Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.abc.def")
        assert "eyJ" not in result
        assert REDACTED in result

    def test_a_key_value_pair_with_a_sensitive_key_is_redacted(self):
        result = redact_message("login failed for api_key=sk_live_abc123xyz")
        assert "sk_live_abc123xyz" not in result

    def test_a_card_number_shaped_run_of_digits_is_redacted(self):
        result = redact_message("charged card 4111111111111111 successfully")
        assert "4111111111111111" not in result

    def test_ordinary_text_is_left_alone(self):
        assert redact_message("user logged in successfully") == "user logged in successfully"

    def test_non_string_input_passes_through_unchanged(self):
        assert redact_message(None) is None
        assert redact_message(42) == 42


class TestFormatterIntegration:
    def test_json_formatter_redacts_a_sensitive_extra_field(self):
        formatter = JsonFormatter()
        record = _record("user login attempt", password="hunter2")
        payload = json.loads(formatter.format(record))
        assert payload["password"] == REDACTED

    def test_json_formatter_redacts_a_sensitive_pattern_in_the_message(self):
        formatter = JsonFormatter()
        record = _record("auth header was Bearer sometoken123456")
        payload = json.loads(formatter.format(record))
        assert "sometoken123456" not in payload["message"]

    def test_text_formatter_redacts_a_sensitive_pattern_in_the_message(self):
        formatter = TextFormatter(TextFormatter.DEFAULT_FORMAT)
        record = _record("auth header was Bearer sometoken123456")
        assert "sometoken123456" not in formatter.format(record)
