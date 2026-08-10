"""
Captcha — Short alphanumeric challenge held in the session, single-use (the
stored code is cleared on every validation attempt, pass or fail).
Category: Core Framework (Security).
Relations:
  - Bound as `captcha`, exposed via the `Captcha` facade. Uses
    `secrets.compare_digest` for the comparison.
References:
  - Guide: `documentation/security.md#captcha-integration`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import random
import secrets
import string
from typing import Any


class Captcha:
    """Generates and validates a short alphanumeric challenge held in session."""

    LENGTH = 5

    @staticmethod
    def generate(request: Any) -> str:
        alphabet = string.ascii_uppercase + string.digits
        code = "".join(secrets.choice(alphabet) for _ in range(Captcha.LENGTH))
        if hasattr(request, "session"):
            request.session().put("captcha_code", code)
        return code

    @staticmethod
    def get_obfuscated_html(code: str) -> str:
        """Render the code as per-character spans with jitter, to resist OCR."""
        spans = []
        for character in code:
            rotation = random.randint(-25, 25)
            offset = random.randint(-3, 3)
            spans.append(
                f'<span style="display:inline-block;'
                f"transform:rotate({rotation}deg) translateY({offset}px);"
                f'padding:0 2px">{character}</span>'
            )
        return f'<span class="craft-captcha">{"".join(spans)}</span>'

    @staticmethod
    def validate(request: Any, code: str) -> bool:
        """Compare against the stored code, clearing it to prevent replay."""
        if not hasattr(request, "session"):
            return False

        stored = request.session().get("captcha_code")
        # Always clear, whether or not the attempt succeeds — a captcha is
        # single-use, otherwise it can be brute-forced against one challenge.
        request.session().forget("captcha_code")

        if not stored or not code:
            return False
        return secrets.compare_digest(str(stored).upper(), str(code).upper())
