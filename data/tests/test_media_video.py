"""Tests for Video processor in Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import os
import tempfile
import pytest

from craft.media.video import Video


@pytest.fixture
def mock_video_file():
    """Create a temporary video file placeholder."""
    fd, path = tempfile.mkstemp(suffix=".mp4")
    with os.fdopen(fd, "wb") as f:
        f.write(b"mock video data 1234567890")
    yield path
    if os.path.exists(path):
        os.remove(path)


class TestVideoProcessing:
    def test_load_video(self, mock_video_file):
        video = Video.load(mock_video_file)
        assert video.filename.endswith(".mp4")
        assert video.filesize > 0

    def test_metadata_keys(self, mock_video_file, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda _: None)
        video = Video.load(mock_video_file)
        meta = video.metadata()
        assert "filename" in meta
        assert "filesize" in meta
        assert "duration" in meta
        assert "width" in meta
        assert "height" in meta
        assert "codec" in meta

    def test_extract_frame_fallback(self, mock_video_file, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda _: None)
        video = Video.load(mock_video_file)
        frame = video.extract_frame(at_seconds=1.5)
        assert frame.width > 0
        assert frame.height > 0

    def test_video_thumbnail(self, mock_video_file, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda _: None)
        video = Video.load(mock_video_file)
        thumb = video.thumbnail(width=320, height=180, format="webp")
        assert thumb.dimensions == (320, 180)
        assert thumb.mime_type == "image/webp"
