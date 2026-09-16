"""The captcha challenge is served as an image, never as readable markup."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import base64
import io
import re

from PIL import Image
from starlette.testclient import TestClient

from bootstrap.app import asgi_app
from craft.security.captcha import Captcha


def test_png_has_the_declared_size() -> None:
    image = Image.open(io.BytesIO(Captcha.render_png("ABCDE")))
    assert image.format == "PNG"
    assert image.size == (Captcha.WIDTH, Captcha.HEIGHT)


def test_alphabet_excludes_ambiguous_characters() -> None:
    assert not set("O0I1") & set(Captcha.ALPHABET)


def test_same_code_renders_differently_each_time() -> None:
    assert Captcha.render_png("ABCDE") != Captcha.render_png("ABCDE")


def test_login_page_never_contains_the_code(migrated_database) -> None:
    client = TestClient(asgi_app)
    page = client.get("/login")
    assert page.status_code == 200
    match = re.search(r'src="data:image/png;base64,([A-Za-z0-9+/=]+)"', page.text)
    assert match, "the challenge must be an inline PNG image"
    Image.open(io.BytesIO(base64.b64decode(match.group(1)))).verify()
    assert "craft-captcha" not in page.text
