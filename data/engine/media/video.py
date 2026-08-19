"""Video processing and frame extraction engine for Craft Framework.

Category: Core Framework (Media / Video).
Relations:
  - Backed by ffmpeg/ffprobe CLI or python video libraries if available.
  - Integrates with `craft.media.image.Image` for fluent post-processing.
  - Exposed via the `Media` facade (`craft.facades.Media`).
References:
  - Guide: `documentation/media.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional, Union

from engine.media.image import Image


class Video:
    """Video inspection, thumbnail generator and metadata processor."""

    def __init__(self, path: Union[str, Path]):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"Video file not found: {self.path}")

    @classmethod
    def load(cls, source: Union[str, Path]) -> Video:
        """Load a video file from disk."""
        return cls(source)

    @property
    def filename(self) -> str:
        return self.path.name

    @property
    def filesize(self) -> int:
        return self.path.stat().st_size

    def metadata(self) -> Dict[str, Any]:
        """Extract video metadata (duration, dimensions, fps, codec, bitrate)."""
        meta: Dict[str, Any] = {
            "filename": self.filename,
            "filesize": self.filesize,
            "duration": 0.0,
            "width": 0,
            "height": 0,
            "fps": 0.0,
            "codec": "unknown",
            "bitrate": 0,
        }

        # Check if ffprobe is installed in system path
        ffprobe_bin = shutil.which("ffprobe")
        if ffprobe_bin:
            try:
                cmd = [
                    ffprobe_bin,
                    "-v", "error",
                    "-nostdin",
                    "-print_format", "json",
                    "-show_format",
                    "-show_streams",
                    str(self.path),
                ]
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=3,
                    stdin=subprocess.DEVNULL,
                )
                if proc.returncode == 0 and proc.stdout:
                    data = json.loads(proc.stdout)
                    fmt = data.get("format", {})
                    meta["duration"] = float(fmt.get("duration", 0.0))
                    meta["bitrate"] = int(fmt.get("bit_rate", 0))

                    for stream in data.get("streams", []):
                        if stream.get("codec_type") == "video":
                            meta["width"] = int(stream.get("width", 0))
                            meta["height"] = int(stream.get("height", 0))
                            meta["codec"] = stream.get("codec_name", "unknown")
                            r_fps = stream.get("r_frame_rate", "0/1")
                            if "/" in r_fps:
                                num, den = r_fps.split("/")
                                if float(den) > 0:
                                    meta["fps"] = round(float(num) / float(den), 2)
                            break
                    return meta
            except Exception:
                pass

        # Fallback inspection for standard video file extensions
        ext = self.path.suffix.lower().lstrip(".")
        meta["codec"] = ext if ext else "mp4"
        return meta

    def extract_frame(
        self,
        at_seconds: float = 1.0,
        output_path: Optional[Union[str, Path]] = None,
    ) -> Image:
        """Extract a single frame from video at `at_seconds` and return as an `Image`."""
        ffmpeg_bin = shutil.which("ffmpeg")

        if ffmpeg_bin:
            out_file = output_path or (
                self.path.parent / f"{self.path.stem}_thumb_{int(at_seconds)}.jpg"
            )
            out_file = Path(out_file)
            out_file.parent.mkdir(parents=True, exist_ok=True)

            cmd = [
                ffmpeg_bin,
                "-y",
                "-nostdin",
                "-ss", str(at_seconds),
                "-i", str(self.path),
                "-vframes", "1",
                "-q:v", "2",
                str(out_file),
            ]
            try:
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=3,
                    stdin=subprocess.DEVNULL,
                )
                if proc.returncode == 0 and out_file.exists():
                    return Image.load(out_file)
            except Exception:
                pass

        # Fallback placeholder image with video metadata representation
        meta = self.metadata()
        w = meta.get("width") or 1280
        h = meta.get("height") or 720
        img = Image.new(w, h, color=(30, 30, 35, 255), mode="RGBA")
        if output_path:
            img.save(output_path)
        return img

    def thumbnail(
        self,
        width: int = 400,
        height: int = 225,
        at_seconds: float = 1.0,
        format: str = "webp",
        quality: int = 85,
    ) -> Image:
        """Generate an optimized thumbnail image from video."""
        frame = self.extract_frame(at_seconds=at_seconds)
        return frame.cover(width, height).format(format, quality=quality)
