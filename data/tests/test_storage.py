"""Tests for Storage Subsystem and Cloud/Local Disks in Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest
from craft.facades import Storage
from craft.storage.drivers.local import LocalStorageDriver
from craft.storage.drivers.s3 import S3StorageDriver


class TestStorage:
    def test_local_storage_put_get_delete(self, tmp_path):
        driver = LocalStorageDriver(root=str(tmp_path / "app"), url="/storage")

        # 1. Put binary/text
        assert driver.put("documents/hello.txt", "Hello Craft Storage") is True
        assert driver.exists("documents/hello.txt") is True

        # 2. Get text and bytes
        assert driver.get_text("documents/hello.txt") == "Hello Craft Storage"
        assert driver.get("documents/hello.txt") == b"Hello Craft Storage"
        assert driver.size("documents/hello.txt") == len(b"Hello Craft Storage")
        assert driver.mime_type("documents/hello.txt") == "text/plain"

        # 3. URL
        assert driver.url("documents/hello.txt") == "/storage/documents/hello.txt"

        # 4. Delete
        assert driver.delete("documents/hello.txt") is True
        assert driver.exists("documents/hello.txt") is False

    def test_storage_facade_integration(self, tmp_path):
        test_driver = LocalStorageDriver(root=str(tmp_path / "facade_test"), url="/storage")
        Storage.set_disk("local", test_driver)

        Storage.put("avatar.png", b"\x89PNG\r\n\x1a\nfakecontent")
        assert Storage.exists("avatar.png") is True
        assert Storage.get("avatar.png") == b"\x89PNG\r\n\x1a\nfakecontent"
        assert Storage.mime_type("avatar.png") == "image/png"
        assert Storage.url("avatar.png") == "/storage/avatar.png"

        Storage.delete("avatar.png")
        assert Storage.exists("avatar.png") is False

    def test_s3_storage_driver_url_generation(self):
        s3 = S3StorageDriver({
            "key": "test_key",
            "secret": "test_secret",
            "region": "sa-east-1",
            "bucket": "my-craft-bucket",
        })
        url = s3.url("uploads/photo.jpg")
        assert url == "https://my-craft-bucket.s3.sa-east-1.amazonaws.com/uploads/photo.jpg"
