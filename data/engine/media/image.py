"""Image manipulation and optimization engine for Craft Framework.

Category: Core Framework (Media / Imaging).
Relations:
  - Backed by Pillow (PIL) for high-performance image processing.
  - Exposed through the `Image` facade (`craft.facades.Image`) and `Media` facade.
  - Integrates with Starlette Response for direct image streaming.
References:
  - Guide: `documentation/media.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import base64
import io
import os
from pathlib import Path
from typing import Any, BinaryIO, Optional, Tuple, Union

try:
    from PIL import Image as PILImage, ImageEnhance, ImageFilter, ImageOps
except ImportError:
    PILImage = None
    ImageEnhance = None
    ImageFilter = None
    ImageOps = None


class Image:
    """Fluent image manipulation and optimization class."""

    def __init__(self, pil_image: Any, original_format: Optional[str] = None):
        if PILImage is None:
            raise RuntimeError(
                "Pillow is required for image manipulation in Craft Framework. "
                "Install it via: pip install pillow"
            )
        self._image: PILImage.Image = pil_image
        self._target_format: str = (original_format or pil_image.format or "PNG").upper()
        self._quality: int = 85
        self._strip_exif: bool = True

    @classmethod
    def load(cls, source: Union[str, Path, bytes, BinaryIO, Any]) -> Image:
        """Load an image from a file path, binary bytes, buffer or UploadFile."""
        if PILImage is None:
            raise RuntimeError("Pillow is required. Install it via: pip install pillow")

        # Support UploadFile or Starlette UploadFile
        if hasattr(source, "file"):
            source = source.file
        elif hasattr(source, "read") and callable(source.read):
            raw = source.read()
            if isinstance(raw, str):
                raw = raw.encode("latin1")
            source = raw

        if isinstance(source, (str, Path)):
            path_str = str(source)
            if not os.path.exists(path_str):
                raise FileNotFoundError(f"Image source not found: {path_str}")
            img = PILImage.open(path_str)
            fmt = img.format
            # Force load into memory so file can be closed
            img.load()
            return cls(img, original_format=fmt)

        if isinstance(source, (bytes, bytearray)):
            bio = io.BytesIO(source)
            img = PILImage.open(bio)
            fmt = img.format
            img.load()
            return cls(img, original_format=fmt)

        if isinstance(source, PILImage.Image):
            return cls(source.copy(), original_format=source.format)

        raise TypeError(f"Unsupported image source type: {type(source)}")

    @classmethod
    def new(
        cls,
        width: int,
        height: int,
        color: Union[str, Tuple[int, ...]] = (255, 255, 255, 0),
        mode: str = "RGBA",
    ) -> Image:
        """Create a new blank canvas image."""
        if PILImage is None:
            raise RuntimeError("Pillow is required.")
        img = PILImage.new(mode, (width, height), color)
        return cls(img, original_format="PNG")

    @property
    def width(self) -> int:
        """Get image width in pixels."""
        return self._image.width

    @property
    def height(self) -> int:
        """Get image height in pixels."""
        return self._image.height

    @property
    def dimensions(self) -> Tuple[int, int]:
        """Get (width, height) tuple."""
        return (self._image.width, self._image.height)

    @property
    def aspect_ratio(self) -> float:
        """Get image aspect ratio (width / height)."""
        return self.width / max(self.height, 1)

    @property
    def mime_type(self) -> str:
        """Get MIME type of current target format."""
        fmt = self._target_format.lower()
        if fmt in ("jpg", "jpeg"):
            return "image/jpeg"
        if fmt == "webp":
            return "image/webp"
        if fmt == "png":
            return "image/png"
        if fmt == "gif":
            return "image/gif"
        if fmt == "avif":
            return "image/avif"
        return f"image/{fmt}"

    def format(self, target_format: str, quality: Optional[int] = None) -> Image:
        """Set output image format (webp, jpeg, png, etc.) and optional quality."""
        fmt = target_format.strip().upper()
        if fmt == "JPG":
            fmt = "JPEG"
        self._target_format = fmt
        if quality is not None:
            self._quality = max(1, min(100, quality))
        return self

    def quality(self, val: int) -> Image:
        """Set output image quality (1 to 100)."""
        self._quality = max(1, min(100, val))
        return self

    def resize(
        self,
        width: Optional[int] = None,
        height: Optional[int] = None,
        maintain_ratio: bool = True,
    ) -> Image:
        """Resize image to target width and/or height."""
        if width is None and height is None:
            return self

        orig_w, orig_h = self.dimensions

        if width is not None and height is None:
            new_w = width
            new_h = int(orig_h * (width / orig_w)) if maintain_ratio else orig_h
        elif height is not None and width is None:
            new_h = height
            new_w = int(orig_w * (height / orig_h)) if maintain_ratio else orig_w
        else:
            if maintain_ratio:
                ratio = min(width / orig_w, height / orig_h)
                new_w = int(orig_w * ratio)
                new_h = int(orig_h * ratio)
            else:
                new_w = width
                new_h = height

        resample = getattr(PILImage, "Resampling", PILImage).LANCZOS
        self._image = self._image.resize((max(1, new_w), max(1, new_h)), resample=resample)
        return self

    def scale(self, factor: float) -> Image:
        """Scale dimensions proportionally by a float factor (e.g. 0.5 for 50%)."""
        if factor <= 0:
            raise ValueError("Scale factor must be greater than 0")
        new_w = max(1, int(self.width * factor))
        new_h = max(1, int(self.height * factor))
        resample = getattr(PILImage, "Resampling", PILImage).LANCZOS
        self._image = self._image.resize((new_w, new_h), resample=resample)
        return self

    def crop(self, width: int, height: int, position: str = "center") -> Image:
        """Crop a box of (width, height) positioned within the image."""
        orig_w, orig_h = self.dimensions
        target_w = min(width, orig_w)
        target_h = min(height, orig_h)

        pos = position.lower()
        if pos == "center":
            left = (orig_w - target_w) // 2
            top = (orig_h - target_h) // 2
        elif pos in ("top-left", "left-top"):
            left, top = 0, 0
        elif pos in ("top-right", "right-top"):
            left = orig_w - target_w
            top = 0
        elif pos in ("bottom-left", "left-bottom"):
            left = 0
            top = orig_h - target_h
        elif pos in ("bottom-right", "right-bottom"):
            left = orig_w - target_w
            top = orig_h - target_h
        elif pos == "top":
            left = (orig_w - target_w) // 2
            top = 0
        elif pos == "bottom":
            left = (orig_w - target_w) // 2
            top = orig_h - target_h
        elif pos == "left":
            left = 0
            top = (orig_h - target_h) // 2
        elif pos == "right":
            left = orig_w - target_w
            top = (orig_h - target_h) // 2
        else:
            left = (orig_w - target_w) // 2
            top = (orig_h - target_h) // 2

        right = left + target_w
        bottom = top + target_h
        self._image = self._image.crop((left, top, right, bottom))
        return self

    def cover(self, width: int, height: int, position: str = "center") -> Image:
        """Resize image to cover target bounds while preserving ratio, then crop overflow."""
        orig_w, orig_h = self.dimensions
        ratio = max(width / orig_w, height / orig_h)
        scaled_w = int(orig_w * ratio)
        scaled_h = int(orig_h * ratio)

        resample = getattr(PILImage, "Resampling", PILImage).LANCZOS
        self._image = self._image.resize((scaled_w, scaled_h), resample=resample)
        return self.crop(width, height, position=position)

    def fit(self, width: int, height: int) -> Image:
        """Alias for cover()."""
        return self.cover(width, height)

    def contain(
        self,
        width: int,
        height: int,
        background: Union[str, Tuple[int, ...]] = (255, 255, 255, 255),
    ) -> Image:
        """Fit image within target dimensions and pad background canvas."""
        self.resize(width, height, maintain_ratio=True)
        canvas = PILImage.new("RGBA", (width, height), background)
        offset_x = (width - self.width) // 2
        offset_y = (height - self.height) // 2
        canvas.paste(self._image, (offset_x, offset_y), self._image if self._image.mode == "RGBA" else None)
        self._image = canvas
        return self

    def thumbnail(self, max_width: int, max_height: int) -> Image:
        """Create a thumbnail fitting within max width and max height."""
        resample = getattr(PILImage, "Resampling", PILImage).LANCZOS
        self._image.thumbnail((max_width, max_height), resample=resample)
        return self

    def rotate(self, degrees: float, expand: bool = True) -> Image:
        """Rotate image clockwise by angle in degrees."""
        resample = getattr(PILImage, "Resampling", PILImage).BICUBIC
        self._image = self._image.rotate(-degrees, expand=expand, resample=resample)
        return self

    def flip(self, horizontal: bool = True, vertical: bool = False) -> Image:
        """Flip image horizontally or vertically."""
        if horizontal:
            self._image = self._image.transpose(PILImage.FLIP_LEFT_RIGHT)
        if vertical:
            self._image = self._image.transpose(PILImage.FLIP_TOP_BOTTOM)
        return self

    def greyscale(self) -> Image:
        """Convert image to greyscale / black-and-white."""
        self._image = ImageOps.grayscale(self._image)
        return self

    def grayscale(self) -> Image:
        """Alias for greyscale()."""
        return self.greyscale()

    def invert(self) -> Image:
        """Invert image color channels."""
        if self._image.mode == "RGBA":
            r, g, b, a = self._image.split()
            rgb = PILImage.merge("RGB", (r, g, b))
            inv = ImageOps.invert(rgb)
            r2, g2, b2 = inv.split()
            self._image = PILImage.merge("RGBA", (r2, g2, b2, a))
        else:
            rgb = self._image.convert("RGB")
            self._image = ImageOps.invert(rgb)
        return self

    def blur(self, radius: float = 2.0) -> Image:
        """Apply gaussian blur filter."""
        self._image = self._image.filter(ImageFilter.GaussianBlur(radius=radius))
        return self

    def sharpen(self, factor: float = 2.0) -> Image:
        """Sharpen image by factor."""
        enhancer = ImageEnhance.Sharpness(self._image)
        self._image = enhancer.enhance(factor)
        return self

    def brightness(self, factor: float) -> Image:
        """Adjust image brightness (1.0 = original, <1.0 = darker, >1.0 = brighter)."""
        enhancer = ImageEnhance.Brightness(self._image)
        self._image = enhancer.enhance(factor)
        return self

    def contrast(self, factor: float) -> Image:
        """Adjust image contrast (1.0 = original)."""
        enhancer = ImageEnhance.Contrast(self._image)
        self._image = enhancer.enhance(factor)
        return self

    def watermark(
        self,
        watermark_source: Union[str, Path, bytes, Image],
        position: str = "bottom-right",
        opacity: float = 0.7,
        padding: int = 10,
    ) -> Image:
        """Apply a watermark image with custom positioning and opacity."""
        if not isinstance(watermark_source, Image):
            wm = Image.load(watermark_source)
        else:
            wm = watermark_source

        # Ensure base and watermark are RGBA for alpha compositing
        base = self._image.convert("RGBA")
        wm_img = wm._image.convert("RGBA")

        # Scale watermark if it exceeds base dimensions
        max_wm_w = int(base.width * 0.5)
        max_wm_h = int(base.height * 0.5)
        if wm_img.width > max_wm_w or wm_img.height > max_wm_h:
            wm.resize(max_wm_w, max_wm_h, maintain_ratio=True)
            wm_img = wm._image.convert("RGBA")

        # Apply opacity to watermark alpha channel
        if opacity < 1.0:
            alpha = wm_img.split()[3]
            alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
            wm_img.putalpha(alpha)

        # Calculate position
        pos = position.lower()
        if pos in ("bottom-right", "right-bottom"):
            x = base.width - wm_img.width - padding
            y = base.height - wm_img.height - padding
        elif pos in ("bottom-left", "left-bottom"):
            x = padding
            y = base.height - wm_img.height - padding
        elif pos in ("top-right", "right-top"):
            x = base.width - wm_img.width - padding
            y = padding
        elif pos in ("top-left", "left-top"):
            x = padding
            y = padding
        elif pos == "center":
            x = (base.width - wm_img.width) // 2
            y = (base.height - wm_img.height) // 2
        else:
            x = base.width - wm_img.width - padding
            y = base.height - wm_img.height - padding

        layer = PILImage.new("RGBA", base.size, (0, 0, 0, 0))
        layer.paste(wm_img, (max(0, x), max(0, y)))
        self._image = PILImage.alpha_composite(base, layer)
        return self

    def optimize(self, quality: int = 80, strip_exif: bool = True) -> Image:
        """Configure image for high optimization and stripped metadata."""
        self._quality = quality
        self._strip_exif = strip_exif
        return self

    def to_bytes(
        self,
        format: Optional[str] = None,
        quality: Optional[int] = None,
    ) -> bytes:
        """Export image as binary bytes in specified format."""
        target_fmt = (format or self._target_format).upper()
        if target_fmt == "JPG":
            target_fmt = "JPEG"

        q = quality if quality is not None else self._quality
        out_img = self._image

        # Handle color mode compatibility
        if target_fmt == "JPEG" and out_img.mode in ("RGBA", "P", "LA"):
            out_img = out_img.convert("RGB")
        elif target_fmt == "PNG" and out_img.mode not in ("RGB", "RGBA", "L", "LA", "P"):
            out_img = out_img.convert("RGBA")

        buf = io.BytesIO()
        save_kwargs: dict[str, Any] = {"format": target_fmt}

        if target_fmt in ("JPEG", "WEBP"):
            save_kwargs["quality"] = q
            save_kwargs["optimize"] = True
        elif target_fmt == "PNG":
            save_kwargs["optimize"] = True

        out_img.save(buf, **save_kwargs)
        return buf.getvalue()

    def to_base64(
        self,
        format: Optional[str] = None,
        quality: Optional[int] = None,
    ) -> str:
        """Export image as a data URI string (e.g. data:image/webp;base64,...)."""
        raw = self.to_bytes(format=format, quality=quality)
        b64 = base64.b64encode(raw).decode("ascii")
        return f"data:{self.mime_type};base64,{b64}"

    def save(
        self,
        destination: Union[str, Path],
        format: Optional[str] = None,
        quality: Optional[int] = None,
    ) -> str:
        """Save image to disk path, creating parent directories if needed."""
        dest_path = Path(destination)
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        if format is None:
            # Infer from file extension if present
            ext = dest_path.suffix.lstrip(".").upper()
            if ext:
                format = ext

        data = self.to_bytes(format=format, quality=quality)
        with open(dest_path, "wb") as f:
            f.write(data)
        return str(dest_path.resolve())

    def response(
        self,
        format: Optional[str] = None,
        quality: Optional[int] = None,
        filename: Optional[str] = None,
    ) -> Any:
        """Return a Starlette streaming Response with proper content-type."""
        from starlette.responses import Response

        raw = self.to_bytes(format=format, quality=quality)
        headers = {
            "Content-Type": self.mime_type,
            "Content-Length": str(len(raw)),
            "Cache-Control": "public, max-age=86400",
        }
        if filename:
            headers["Content-Disposition"] = f'inline; filename="{filename}"'

        return Response(content=raw, headers=headers, media_type=self.mime_type)
