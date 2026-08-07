"""Request class for Craft Framework.

Wraps Starlette's request with expressive input access. The body is parsed
once, up front, by `prepare()` — controllers and middleware are synchronous, so
they cannot await `request.form()` themselves.

Category: Core Framework (HTTP).
Relations:
  - Built by `services/http/kernel.py` per request; read by
    `services/http/controller.py`, middleware, and `FormRequest`
    (`services/validation/form_request.py`).
References:
  - Guide: `documentation/controllers.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from typing import Any, Dict, Optional

from starlette.datastructures import UploadFile
from starlette.requests import Request as StarletteRequest


class Request(StarletteRequest):
    """The request object handed to middleware and controllers."""

    async def prepare(self) -> "Request":
        """Parse query string and body into a single input bag."""
        if getattr(self, "_input", None) is not None:
            return self

        data: Dict[str, Any] = dict(self.query_params)
        body_data: Dict[str, Any] = {}
        files: Dict[str, UploadFile] = {}

        if self.method not in ("GET", "HEAD", "OPTIONS"):
            content_type = self.headers.get("content-type", "")
            try:
                if "application/json" in content_type:
                    body = await self.json()
                    if isinstance(body, dict):
                        body_data.update(body)
                    else:
                        body_data["__body"] = body
                elif content_type.startswith(
                    ("application/x-www-form-urlencoded", "multipart/form-data")
                ):
                    form = await self.form()
                    for key, value in form.multi_items():
                        if isinstance(value, UploadFile):
                            files[key] = value
                        else:
                            body_data[key] = value
            except Exception:
                # A malformed body is not a crash — it is simply no input.
                pass

        data.update(body_data)
        self._input = data
        self._post = body_data
        self._files = files
        return self

    # -- input access ----------------------------------------------------------

    def all(self) -> Dict[str, Any]:
        return dict(getattr(self, "_input", None) or {})

    def input(self, key: Optional[str] = None, default: Any = None) -> Any:
        if key is None:
            return self.all()
        return self.all().get(key, default)

    def get_input(self, key: Optional[str] = None, default: Any = None) -> Any:
        """Alias of :meth:`input`."""
        return self.input(key, default)

    def post(self, key: Optional[str] = None, default: Any = None) -> Any:
        """Input from the parsed request body only — never the query string."""
        body = dict(getattr(self, "_post", None) or {})
        if key is None:
            return body
        return body.get(key, default)

    def only(self, *keys: str) -> Dict[str, Any]:
        data = self.all()
        return {k: data[k] for k in keys if k in data}

    def except_(self, *keys: str) -> Dict[str, Any]:
        return {k: v for k, v in self.all().items() if k not in keys}

    def has(self, *keys: str) -> bool:
        data = self.all()
        return all(k in data for k in keys)

    def missing(self, key: str) -> bool:
        return not self.has(key)

    def filled(self, *keys: str) -> bool:
        data = self.all()
        return all(data.get(k) not in (None, "", [], {}) for k in keys)

    def boolean(self, key: str, default: bool = False) -> bool:
        value = self.input(key)
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ("1", "true", "on", "yes")

    def integer(self, key: str, default: Optional[int] = None) -> Optional[int]:
        try:
            return int(self.input(key))
        except (TypeError, ValueError):
            return default

    def file(self, key: str) -> Optional[UploadFile]:
        return getattr(self, "_files", None) and self._files.get(key) or None

    def files(self) -> Dict[str, UploadFile]:
        return dict(getattr(self, "_files", None) or {})

    # -- session ---------------------------------------------------------------

    def session(self) -> Any:
        """The session bag, attached by the StartSession middleware."""
        session = getattr(self.state, "session", None)
        if session is None:
            raise RuntimeError(
                "No session on this request. Add StartSession to the middleware "
                "stack in bootstrap/app.py."
            )
        return session

    def has_session(self) -> bool:
        return getattr(self.state, "session", None) is not None

    def user(self) -> Any:
        """The authenticated user, if any."""
        from services.container.application import Container

        try:
            return Container.getInstance().make("auth").user()
        except Exception:
            return None

    # -- content negotiation ---------------------------------------------------

    def expects_json(self) -> bool:
        accept = self.headers.get("accept", "")
        content_type = self.headers.get("content-type", "")
        if "application/json" in accept or "application/json" in content_type:
            return True
        return self.is_ajax() and "text/html" not in accept

    def wants_json(self) -> bool:
        return self.expects_json()

    def is_ajax(self) -> bool:
        return self.headers.get("x-requested-with", "").lower() == "xmlhttprequest"

    def bearer_token(self) -> Optional[str]:
        header = self.headers.get("authorization", "")
        if header.lower().startswith("bearer "):
            return header[7:].strip()
        return None

    def ip(self) -> Optional[str]:
        # X-Forwarded-For is client-controlled: honour it only when the app is
        # explicitly deployed behind a trusted proxy (config, default off).
        trusted = None
        try:
            from services.container.application import Container

            trusted = Container.getInstance().make("config").get("app.trusted_proxies")
        except Exception:
            trusted = None

        if trusted:
            forwarded = self.headers.get("x-forwarded-for")
            if forwarded:
                return forwarded.split(",")[0].strip()
        return self.client.host if self.client else None

    def path(self) -> str:
        return self.url.path

    def is_method(self, method: str) -> bool:
        return self.method.upper() == method.upper()


def from_starlette(request: StarletteRequest) -> Request:
    """Rebuild a Starlette request as a Craft request, sharing scope and state."""
    if isinstance(request, Request):
        return request
    return Request(request.scope, request.receive)


__all__ = ["Request", "from_starlette"]
