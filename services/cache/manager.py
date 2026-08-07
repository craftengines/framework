"""Cache manager for Codepy Framework.

Supports `array` (in-process), `file` and `redis` stores behind a single
expressive API. TTLs are honoured by every store.
"""
# Codepy Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from typing import Any, Callable, Dict, Optional


class Store:
    def get(self, key: str) -> Any:
        raise NotImplementedError

    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        raise NotImplementedError

    def forget(self, key: str) -> None:
        raise NotImplementedError

    def flush(self) -> None:
        raise NotImplementedError


class ArrayStore(Store):
    """In-memory store — the default, and the store used during tests."""

    def __init__(self) -> None:
        self._items: Dict[str, tuple] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any:
        with self._lock:
            entry = self._items.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if expires_at is not None and expires_at < time.time():
                del self._items[key]
                return None
            return value

    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        with self._lock:
            self._items[key] = (value, time.time() + ttl if ttl else None)

    def forget(self, key: str) -> None:
        with self._lock:
            self._items.pop(key, None)

    def flush(self) -> None:
        with self._lock:
            self._items.clear()


class FileStore(Store):
    """Filesystem store writing JSON payloads under `storage/framework/cache`."""

    def __init__(self, directory: str):
        self.directory = directory
        os.makedirs(self.directory, exist_ok=True)

    def _path(self, key: str) -> str:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return os.path.join(self.directory, f"{digest}.cache")

    def get(self, key: str) -> Any:
        path = self._path(key)
        if not os.path.isfile(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (json.JSONDecodeError, OSError):
            return None
        if payload.get("expires_at") and payload["expires_at"] < time.time():
            self.forget(key)
            return None
        return payload.get("value")

    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        payload = {"value": value, "expires_at": time.time() + ttl if ttl else None}
        try:
            with open(self._path(key), "w", encoding="utf-8") as handle:
                json.dump(payload, handle)
        except (TypeError, OSError):
            pass

    def forget(self, key: str) -> None:
        try:
            os.remove(self._path(key))
        except OSError:
            pass

    def flush(self) -> None:
        if not os.path.isdir(self.directory):
            return
        for name in os.listdir(self.directory):
            if name.endswith(".cache"):
                try:
                    os.remove(os.path.join(self.directory, name))
                except OSError:
                    pass


class RedisStore(Store):
    """Redis-backed store. Requires the `redis` package."""

    def __init__(self, host: str = "127.0.0.1", port: int = 6379, password: Optional[str] = None, db: int = 0):
        import redis  # imported lazily so redis stays optional

        self.client = redis.Redis(host=host, port=port, password=password or None, db=db)

    def get(self, key: str) -> Any:
        raw = self.client.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw

    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        payload = json.dumps(value, default=str)
        if ttl:
            self.client.setex(key, int(ttl), payload)
        else:
            self.client.set(key, payload)

    def forget(self, key: str) -> None:
        self.client.delete(key)

    def flush(self) -> None:
        self.client.flushdb()


class CacheManager:
    """Resolves the configured store and exposes the cache API."""

    def __init__(self, app: Any = None):
        self.app = app
        self._store: Optional[Store] = None

    @property
    def store(self) -> Store:
        if self._store is None:
            self._store = self._resolve_store()
        return self._store

    def _resolve_store(self) -> Store:
        config = None
        if self.app is not None:
            try:
                config = self.app.make("config")
            except Exception:
                config = None

        driver = (config.get("cache.default", "array") if config else "array") or "array"
        driver = str(driver).lower()

        if driver == "file":
            base_path = getattr(self.app, "base_path", os.getcwd())
            directory = (
                config.get("cache.stores.file.path") if config else None
            ) or os.path.join(base_path, "storage", "framework", "cache")
            return FileStore(directory)

        if driver == "redis":
            try:
                return RedisStore(
                    host=(config.get("cache.stores.redis.host", "127.0.0.1") if config else "127.0.0.1"),
                    port=int(config.get("cache.stores.redis.port", 6379) if config else 6379),
                    password=(config.get("cache.stores.redis.password") if config else None),
                )
            except Exception:
                # Redis unavailable — degrade to in-memory rather than break the app.
                return ArrayStore()

        return ArrayStore()

    # -- public API ------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        value = self.store.get(key)
        return default if value is None else value

    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        self.store.put(key, value, ttl)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        self.put(key, value, ttl)

    def has(self, key: str) -> bool:
        return self.store.get(key) is not None

    def forget(self, key: str) -> None:
        self.store.forget(key)

    def forever(self, key: str, value: Any) -> None:
        self.store.put(key, value, None)

    def flush(self) -> None:
        self.store.flush()

    def remember(self, key: str, ttl: Optional[int], callback: Callable[[], Any]) -> Any:
        cached = self.store.get(key)
        if cached is not None:
            return cached
        value = callback()
        self.store.put(key, value, ttl)
        return value

    def remember_forever(self, key: str, callback: Callable[[], Any]) -> Any:
        return self.remember(key, None, callback)

    def pull(self, key: str, default: Any = None) -> Any:
        value = self.get(key, default)
        self.forget(key)
        return value

    def increment(self, key: str, amount: int = 1) -> int:
        value = int(self.get(key, 0) or 0) + amount
        self.forever(key, value)
        return value

    def decrement(self, key: str, amount: int = 1) -> int:
        return self.increment(key, -amount)


__all__ = ["CacheManager", "ArrayStore", "FileStore", "RedisStore", "Store"]
