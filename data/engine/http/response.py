"""
Response — Response/JsonResponse wrappers and the `redirect()` helper.
Category: Core Framework (HTTP).
Relations:
  - Returned by `engine/http/controller.py` helpers; converted to a
    Starlette response by `engine/http/kernel.py`.
References:
  - Guide: `documentation/controllers.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import json
from typing import Any, Dict, Optional
from starlette.responses import Response as StarletteResponse, JSONResponse as StarletteJSONResponse, HTMLResponse as StarletteHTMLResponse, RedirectResponse as StarletteRedirectResponse


class Response:
    def __init__(self, content: Any = "", status: int = 200, headers: Optional[Dict[str, str]] = None):
        self._content = content
        self._status = status
        self._headers = headers or {}

    def to_starlette(self) -> StarletteResponse:
        if isinstance(self._content, (dict, list)):
            return JsonResponse(self._content, self._status, self._headers).to_starlette()
        return StarletteHTMLResponse(str(self._content), status_code=self._status, headers=self._headers)


class JsonResponse(Response):
    def __init__(self, content: Any = None, status: int = 200, headers: Optional[Dict[str, str]] = None):
        if content is None:
            content = {}
        super().__init__(content, status, headers)

    def to_starlette(self) -> StarletteResponse:
        content = self._serialize(self._content)
        return StarletteJSONResponse(content, status_code=self._status, headers=self._headers)

    def _serialize(self, obj: Any) -> Any:
        if isinstance(obj, list):
            return [self._serialize(item) for item in obj]
        if isinstance(obj, dict):
            return {k: self._serialize(v) for k, v in obj.items()}
        if hasattr(obj, "to_array"):
            return self._serialize(obj.to_array())
        if hasattr(obj, "to_dict"):
            return self._serialize(obj.to_dict())
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        return obj


def redirect(url: str = "", route: Optional[str] = None, status: int = 302, **kwargs) -> StarletteResponse:
    if route:
        from engine.facades import Route
        target_url = Route.url_for(route, **kwargs)
    else:
        target_url = url
    return StarletteRedirectResponse(url=target_url, status_code=status)
