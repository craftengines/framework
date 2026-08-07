"""Session handling for Craft Framework.

Two drivers ship by default:

* ``cookie`` — the whole payload lives in a signed cookie. No storage to set up,
  but the data is visible to the client and capped by cookie size.
* ``file``   — the cookie holds only an id; the payload lives under
  ``storage/framework/sessions``. Supports server-side invalidation.

Both sign the cookie with the application key, so a tampered cookie is rejected
rather than trusted.

Category: Core Framework (HTTP).
Relations:
  - Started by `StartSession` middleware (`services/http/middleware.py`);
    read via `request.session()`; CSRF verification in the same middleware
    module consumes the session's token.
References:
  - Guide: `documentation/sessions.md`, `documentation/security.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from contextvars import ContextVar
from typing import Any, Dict, List, Optional

#: The session for the request being handled, set by the StartSession
#: middleware. Lets view helpers such as `csrf_field()` reach it without every
#: caller threading the request through.
current_session: ContextVar[Optional["Session"]] = ContextVar("current_session", default=None)


def get_current_session() -> Optional["Session"]:
    return current_session.get()

#: Keys used internally to carry flash data across exactly one request.
_FLASH_NEW = "__flash_new"
_FLASH_OLD = "__flash_old"
_TOKEN = "__csrf_token"


class Session:
    """Per-request session bag."""

    def __init__(self, data: Optional[Dict[str, Any]] = None, session_id: Optional[str] = None):
        self._data: Dict[str, Any] = dict(data or {})
        self.id = session_id or secrets.token_urlsafe(24)
        #: The id this session was loaded with — lets the store destroy the old
        #: file when regenerate()/invalidate() hands out a new id.
        self._original_id = self.id
        self._modified = False

        # Data flashed on the previous request is readable now and then dropped.
        self._data[_FLASH_OLD] = self._data.pop(_FLASH_NEW, [])

    # -- basic access ----------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def put(self, key: str, value: Any) -> None:
        self._data[key] = value
        self._modified = True

    def set(self, key: str, value: Any) -> None:
        self.put(key, value)

    def has(self, key: str) -> bool:
        return self._data.get(key) is not None

    def exists(self, key: str) -> bool:
        return key in self._data

    def forget(self, key: str) -> None:
        if key in self._data:
            del self._data[key]
            self._modified = True

    def pull(self, key: str, default: Any = None) -> Any:
        value = self.get(key, default)
        self.forget(key)
        return value

    def all(self) -> Dict[str, Any]:
        return {k: v for k, v in self._data.items() if not k.startswith("__")}

    def flush(self) -> None:
        """Drop every value but keep the session (and its CSRF token) alive."""
        token = self._data.get(_TOKEN)
        self._data = {}
        if token:
            self._data[_TOKEN] = token
        self._modified = True

    def invalidate(self) -> None:
        """Drop everything and take a new id — use after login/logout."""
        self._data = {}
        self.id = secrets.token_urlsafe(24)
        self.regenerate_token()
        self._modified = True

    def regenerate(self) -> None:
        """New id, same data — mitigates session fixation."""
        self.id = secrets.token_urlsafe(24)
        self._modified = True

    # -- flash data ------------------------------------------------------------

    def flash(self, key: str, value: Any) -> None:
        """Store a value readable on the next request only."""
        self._data[key] = value
        queued: List[str] = list(self._data.get(_FLASH_NEW, []))
        if key not in queued:
            queued.append(key)
        self._data[_FLASH_NEW] = queued
        self._modified = True

    def reflash(self) -> None:
        """Keep the current request's flash data for one more request."""
        old = list(self._data.get(_FLASH_OLD, []))
        self._data[_FLASH_NEW] = list(set(self._data.get(_FLASH_NEW, [])) | set(old))
        self._modified = True

    def age_flash_data(self) -> None:
        """Expire the previous request's flash keys. Called on save."""
        for key in self._data.get(_FLASH_OLD, []):
            if key not in self._data.get(_FLASH_NEW, []):
                self._data.pop(key, None)
        self._data.pop(_FLASH_OLD, None)

    # -- CSRF ------------------------------------------------------------------

    def token(self) -> str:
        """The CSRF token, created on first use."""
        if not self._data.get(_TOKEN):
            self.regenerate_token()
        return self._data[_TOKEN]

    def regenerate_token(self) -> str:
        self._data[_TOKEN] = secrets.token_urlsafe(32)
        self._modified = True
        return self._data[_TOKEN]

    # -- serialization ---------------------------------------------------------

    @property
    def modified(self) -> bool:
        return self._modified

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._data)

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.put(key, value)

    def __repr__(self) -> str:
        return f"<Session {self.id[:8]}… {list(self.all())}>"


# -- signing --------------------------------------------------------------------

def sign(payload: str, key: str) -> str:
    digest = hmac.new(key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def verify(payload: str, signature: str, key: str) -> bool:
    return hmac.compare_digest(sign(payload, key), signature)


class SessionStore:
    """Base store: turns a Session into a cookie value and back."""

    def __init__(self, key: str, lifetime: int = 7200):
        self.key = key
        self.lifetime = lifetime

    def load(self, cookie_value: Optional[str]) -> Session:  # pragma: no cover
        raise NotImplementedError

    def save(self, session: Session) -> str:  # pragma: no cover
        raise NotImplementedError

    # -- shared helpers --------------------------------------------------------

    def _encode(self, data: Dict[str, Any]) -> str:
        raw = json.dumps(data, separators=(",", ":"), default=str)
        encoded = base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii").rstrip("=")
        return f"{encoded}.{sign(encoded, self.key)}"

    def _decode(self, value: str) -> Optional[Dict[str, Any]]:
        if not value or "." not in value:
            return None
        encoded, _, signature = value.rpartition(".")
        if not verify(encoded, signature, self.key):
            return None  # tampered or signed with a different app key
        try:
            padding = "=" * (-len(encoded) % 4)
            raw = base64.urlsafe_b64decode(encoded + padding).decode("utf-8")
            data = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            return None
        if not isinstance(data, dict):
            return None
        expires_at = data.pop("__expires_at", None)
        if expires_at is not None and float(expires_at) < time.time():
            return None
        return data


class CookieSessionStore(SessionStore):
    """Stores the whole payload in the signed cookie."""

    def load(self, cookie_value: Optional[str]) -> Session:
        data = self._decode(cookie_value) if cookie_value else None
        return Session(data or {})

    def save(self, session: Session) -> str:
        session.age_flash_data()
        data = session.to_dict()
        data["__expires_at"] = time.time() + self.lifetime
        return self._encode(data)


class FileSessionStore(SessionStore):
    """Stores the payload on disk; the cookie carries only a signed id."""

    def __init__(self, key: str, directory: str, lifetime: int = 7200):
        super().__init__(key, lifetime)
        self.directory = directory
        os.makedirs(self.directory, exist_ok=True)

    def _path(self, session_id: str) -> str:
        # Hash the id so a crafted id can never escape the directory.
        digest = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
        return os.path.join(self.directory, f"{digest}.session")

    def load(self, cookie_value: Optional[str]) -> Session:
        payload = self._decode(cookie_value) if cookie_value else None
        session_id = (payload or {}).get("id")
        if not session_id:
            return Session({})

        path = self._path(session_id)
        if not os.path.isfile(path):
            return Session({}, session_id=session_id)

        try:
            with open(path, "r", encoding="utf-8") as handle:
                stored = json.load(handle)
        except (OSError, ValueError):
            return Session({}, session_id=session_id)

        if stored.get("__expires_at", 0) < time.time():
            self.destroy(session_id)
            return Session({}, session_id=session_id)

        stored.pop("__expires_at", None)
        return Session(stored, session_id=session_id)

    def save(self, session: Session) -> str:
        session.age_flash_data()
        data = session.to_dict()
        data["__expires_at"] = time.time() + self.lifetime

        # regenerate()/invalidate() changed the id — destroy the old file so a
        # fixated cookie cannot keep resurrecting the pre-rotation session.
        original_id = getattr(session, "_original_id", None)
        if original_id and original_id != session.id:
            self.destroy(original_id)
            session._original_id = session.id

        try:
            with open(self._path(session.id), "w", encoding="utf-8") as handle:
                json.dump(data, handle, default=str)
        except OSError:
            pass
        return self._encode({"id": session.id})

    def destroy(self, session_id: str) -> None:
        try:
            os.remove(self._path(session_id))
        except OSError:
            pass

    def gc(self) -> int:
        """Delete expired session files. Returns how many were removed."""
        removed = 0
        if not os.path.isdir(self.directory):
            return 0
        for name in os.listdir(self.directory):
            if not name.endswith(".session"):
                continue
            path = os.path.join(self.directory, name)
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    stored = json.load(handle)
                if stored.get("__expires_at", 0) < time.time():
                    os.remove(path)
                    removed += 1
            except (OSError, ValueError):
                continue
        return removed


#: One fallback signing key per process, created on first use. It must be
#: stable — a fresh key per store instance would silently invalidate every
#: cookie the moment anything rebuilt the store.
_EPHEMERAL_KEY: Optional[str] = None


def _ephemeral_key() -> str:
    global _EPHEMERAL_KEY
    if _EPHEMERAL_KEY is None:
        _EPHEMERAL_KEY = secrets.token_urlsafe(32)
    return _EPHEMERAL_KEY


def make_store(app: Any = None) -> SessionStore:
    """Build the configured session store."""
    config = None
    if app is not None:
        try:
            config = app.make("config")
        except Exception:
            config = None

    def setting(key: str, default: Any) -> Any:
        return config.get(key, default) if config else default

    app_key = str(setting("app.APP_KEY", "") or setting("app.app_key", "") or "")
    if not app_key:
        # Never sign with an empty key — that would make forgery trivial. Fall
        # back to one random key per process: sessions work, but they do not
        # survive a restart and are not shared between workers, until
        # `dev key:generate` writes a real APP_KEY.
        app_key = _ephemeral_key()

    lifetime = int(setting("session.lifetime", 7200) or 7200)
    driver = str(setting("session.driver", "cookie") or "cookie").lower()

    if driver == "file":
        base_path = getattr(app, "base_path", os.getcwd())
        directory = setting(
            "session.files", os.path.join(base_path, "storage", "framework", "sessions")
        )
        return FileSessionStore(app_key, directory, lifetime)

    return CookieSessionStore(app_key, lifetime)


__all__ = [
    "Session",
    "SessionStore",
    "CookieSessionStore",
    "FileSessionStore",
    "make_store",
    "sign",
    "verify",
    "current_session",
    "get_current_session",
]
