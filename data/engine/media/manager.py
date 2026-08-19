"""Media & Imaging manager for Craft Framework.

Category: Core Framework (Media).
Relations:
  - Backs `Image` and `Media` facades.
  - Interacts with Container and Storage.
References:
  - Guide: `documentation/media.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from pathlib import Path
from typing import Any, BinaryIO, Optional, Tuple, Union

from engine.media.image import Image
from engine.media.video import Video


class ImageManager:
    """Entry point for image creation, loading and manipulation."""

    def __init__(self, app: Optional[Any] = None):
        self.app = app

    def load(self, source: Union[str, Path, bytes, BinaryIO, Any]) -> Image:
        """Load an existing image from path, buffer or UploadFile."""
        return Image.load(source)

    def new(
        self,
        width: int,
        height: int,
        color: Union[str, Tuple[int, ...]] = (255, 255, 255, 0),
        mode: str = "RGBA",
    ) -> Image:
        """Create a new blank canvas."""
        return Image.new(width, height, color, mode)


class MediaManager:
    """Unified multimedia manager for images and videos."""

    def __init__(self, app: Optional[Any] = None):
        self.app = app
        self._image_mgr = ImageManager(app)

    def image(self, source: Union[str, Path, bytes, BinaryIO, Any]) -> Image:
        """Create a fluent Image manipulation instance."""
        return self._image_mgr.load(source)

    def new_image(
        self,
        width: int,
        height: int,
        color: Union[str, Tuple[int, ...]] = (255, 255, 255, 0),
        mode: str = "RGBA",
    ) -> Image:
        """Create a new blank Image."""
        return self._image_mgr.new(width, height, color, mode)

    def video(self, source: Union[str, Path]) -> Video:
        """Create a Video inspection and thumbnail instance."""
        return Video.load(source)
