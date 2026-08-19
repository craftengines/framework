"""Tests for Image manipulation, transformations, and optimization in Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import io
import os
import tempfile
import pytest

from PIL import Image as PILImage
from craft.media.image import Image
from craft.facades import Image as ImageFacade


@pytest.fixture
def sample_image_bytes():
    """Generate in-memory sample PNG image bytes (100x60, blue)."""
    img = PILImage.new("RGBA", (100, 60), (0, 100, 200, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def sample_image_file(sample_image_bytes):
    """Write sample image to temporary file on disk."""
    fd, path = tempfile.mkstemp(suffix=".png")
    with os.fdopen(fd, "wb") as f:
        f.write(sample_image_bytes)
    yield path
    if os.path.exists(path):
        os.remove(path)


class TestImageLoading:
    def test_load_from_bytes(self, sample_image_bytes):
        img = Image.load(sample_image_bytes)
        assert img.width == 100
        assert img.height == 60
        assert img.dimensions == (100, 60)
        assert img.aspect_ratio == pytest.approx(100 / 60)

    def test_load_from_file_path(self, sample_image_file):
        img = Image.load(sample_image_file)
        assert img.width == 100
        assert img.height == 60

    def test_load_nonexistent_file_raises(self):
        with pytest.raises(FileNotFoundError):
            Image.load("non_existent_file_12345.png")

    def test_create_new_blank_image(self):
        img = Image.new(200, 150, color=(255, 0, 0, 255))
        assert img.width == 200
        assert img.height == 150


class TestImageTransformations:
    def test_resize_proportional(self, sample_image_bytes):
        img = Image.load(sample_image_bytes).resize(width=50)
        assert img.width == 50
        assert img.height == 30

    def test_resize_explicit_dimensions_without_ratio(self, sample_image_bytes):
        img = Image.load(sample_image_bytes).resize(width=40, height=40, maintain_ratio=False)
        assert img.dimensions == (40, 40)

    def test_scale_factor(self, sample_image_bytes):
        img = Image.load(sample_image_bytes).scale(0.5)
        assert img.dimensions == (50, 30)

    def test_crop_positions(self, sample_image_bytes):
        # 100x60 -> crop 40x40 center
        img_center = Image.load(sample_image_bytes).crop(40, 40, position="center")
        assert img_center.dimensions == (40, 40)

        img_tl = Image.load(sample_image_bytes).crop(30, 30, position="top-left")
        assert img_tl.dimensions == (30, 30)

        img_br = Image.load(sample_image_bytes).crop(30, 30, position="bottom-right")
        assert img_br.dimensions == (30, 30)

    def test_cover_and_fit(self, sample_image_bytes):
        img = Image.load(sample_image_bytes).cover(50, 50)
        assert img.dimensions == (50, 50)

        img_fit = Image.load(sample_image_bytes).fit(40, 40)
        assert img_fit.dimensions == (40, 40)

    def test_contain_with_padding(self, sample_image_bytes):
        img = Image.load(sample_image_bytes).contain(120, 120, background=(255, 255, 255, 255))
        assert img.dimensions == (120, 120)

    def test_thumbnail(self, sample_image_bytes):
        img = Image.load(sample_image_bytes).thumbnail(50, 50)
        assert img.width <= 50
        assert img.height <= 50
        assert img.dimensions == (50, 30)


class TestImageFiltersAndEffects:
    def test_rotation(self, sample_image_bytes):
        img = Image.load(sample_image_bytes).rotate(90, expand=True)
        assert img.dimensions == (60, 100)

    def test_flip_horizontal_and_vertical(self, sample_image_bytes):
        img = Image.load(sample_image_bytes).flip(horizontal=True, vertical=True)
        assert img.dimensions == (100, 60)

    def test_greyscale(self, sample_image_bytes):
        img = Image.load(sample_image_bytes).greyscale()
        raw = img.to_bytes(format="PNG")
        assert len(raw) > 0

    def test_blur_and_sharpen(self, sample_image_bytes):
        img = Image.load(sample_image_bytes).blur(radius=1.5).sharpen(factor=1.8)
        assert img.dimensions == (100, 60)

    def test_brightness_and_contrast(self, sample_image_bytes):
        img = Image.load(sample_image_bytes).brightness(1.2).contrast(1.1)
        assert img.dimensions == (100, 60)

    def test_invert(self, sample_image_bytes):
        img = Image.load(sample_image_bytes).invert()
        assert img.dimensions == (100, 60)

    def test_watermark(self, sample_image_bytes):
        wm = Image.new(20, 20, color=(255, 255, 255, 200))
        img = Image.load(sample_image_bytes).watermark(wm, position="bottom-right", opacity=0.8)
        assert img.dimensions == (100, 60)


class TestImageFormatsAndExport:
    def test_convert_to_webp(self, sample_image_bytes):
        img = Image.load(sample_image_bytes).format("webp", quality=80)
        assert img.mime_type == "image/webp"
        raw = img.to_bytes()
        assert len(raw) > 0

    def test_convert_to_jpeg(self, sample_image_bytes):
        img = Image.load(sample_image_bytes).format("jpeg", quality=90)
        assert img.mime_type == "image/jpeg"
        raw = img.to_bytes()
        assert len(raw) > 0

    def test_to_base64(self, sample_image_bytes):
        b64 = Image.load(sample_image_bytes).format("png").to_base64()
        assert b64.startswith("data:image/png;base64,")

    def test_save_to_disk(self, sample_image_bytes):
        temp_dir = tempfile.mkdtemp()
        dest = os.path.join(temp_dir, "nested", "output.webp")
        saved_path = Image.load(sample_image_bytes).format("webp").save(dest)
        assert os.path.exists(saved_path)
        assert saved_path.endswith("output.webp")

    def test_starlette_response(self, sample_image_bytes):
        resp = Image.load(sample_image_bytes).format("webp").response(filename="avatar.webp")
        assert resp.headers["Content-Type"] == "image/webp"
        assert "avatar.webp" in resp.headers["Content-Disposition"]
