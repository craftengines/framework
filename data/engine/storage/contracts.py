"""Storage Driver Protocol and Contracts for Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from typing import Any, BinaryIO, Optional, Protocol, Union


class StorageDriver(Protocol):
    """Storage filesystem driver protocol."""

    def put(self, path: str, contents: Union[str, bytes, BinaryIO], **kwargs: Any) -> bool:
        """Write contents to storage path."""
        ...

    def get(self, path: str) -> Optional[bytes]:
        """Read binary contents from storage path."""
        ...

    def exists(self, path: str) -> bool:
        """Check if file exists at path."""
        ...

    def delete(self, path: str) -> bool:
        """Delete file at path."""
        ...

    def url(self, path: str) -> str:
        """Get public or accessible URL for file."""
        ...

    def temporary_url(self, path: str, minutes: int = 5) -> str:
        """Get signed temporary URL for file."""
        ...

    def size(self, path: str) -> int:
        """Get file size in bytes."""
        ...

    def mime_type(self, path: str) -> str:
        """Get file MIME type."""
        ...
