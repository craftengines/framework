"""Static files handler with explicit RFC-compliant cache policy.

Category: Core Framework (HTTP).
Relations:
  - Subclasses Starlette's `StaticFiles`.
  - Mounted by `engine/http/kernel.py` for public asset directories.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import os
from urllib.parse import parse_qs

from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

#: Query parameter that carries the content fingerprint of an asset.
FINGERPRINT_PARAM = "v"

#: A fingerprinted asset never changes at its address: one year, immutable.
IMMUTABLE_CACHE_CONTROL = "public, max-age=31536000, immutable"

#: A bare asset is shared and revalidated: five minutes of freshness.
REVALIDATED_CACHE_CONTROL = "public, max-age=300, must-revalidate"


def cache_control_for(query_string: bytes) -> str:
    """Return the `Cache-Control` value an asset URL deserves.

    Args:
        query_string: The raw query string of the request scope.

    Returns:
        The immutable policy when the query carries a non-empty fingerprint (`?v=...`),
        or the revalidated policy otherwise.
    """
    params = parse_qs(query_string.decode("latin-1"), keep_blank_values=False)
    if params.get(FINGERPRINT_PARAM):
        return IMMUTABLE_CACHE_CONTROL
    return REVALIDATED_CACHE_CONTROL


class CachedStaticFiles(StaticFiles):
    """`StaticFiles` whose 200 and 304 responses carry explicit `Cache-Control` headers."""

    def file_response(
        self,
        full_path: os.PathLike,
        stat_result: os.stat_result,
        scope: Scope,
        status_code: int = 200,
    ) -> Response:
        """Build the file response and apply the appropriate cache policy header.

        Args:
            full_path: Resolved path of the file on disk.
            stat_result: `os.stat` result of that file.
            scope: ASGI scope of the request.
            status_code: HTTP status of the response.

        Returns:
            The base handler's response with `Cache-Control` stamped.
        """
        response = super().file_response(full_path, stat_result, scope, status_code)
        response.headers["Cache-Control"] = cache_control_for(scope.get("query_string", b""))
        return response


__all__ = [
    "FINGERPRINT_PARAM",
    "IMMUTABLE_CACHE_CONTROL",
    "REVALIDATED_CACHE_CONTROL",
    "cache_control_for",
    "CachedStaticFiles",
]
