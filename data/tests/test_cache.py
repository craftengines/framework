"""Cache manager and stores."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import time

import pytest

from services.cache.manager import ArrayStore, CacheManager, FileStore


@pytest.fixture(params=["array", "file"])
def store(request, tmp_path):
    return ArrayStore() if request.param == "array" else FileStore(str(tmp_path / "cache"))


@pytest.fixture
def cache(store):
    manager = CacheManager()
    manager._store = store
    return manager


class TestStores:
    def test_put_and_get(self, cache):
        cache.put("key", "value")
        assert cache.get("key") == "value"

    def test_missing_key_returns_the_default(self, cache):
        assert cache.get("nope", "fallback") == "fallback"

    def test_missing_key_returns_none_without_a_default(self, cache):
        assert cache.get("nope") is None

    def test_structured_values_survive_a_roundtrip(self, cache):
        cache.put("payload", {"a": [1, 2], "b": {"c": True}})
        assert cache.get("payload") == {"a": [1, 2], "b": {"c": True}}

    def test_has(self, cache):
        cache.put("key", 1)
        assert cache.has("key") is True
        assert cache.has("other") is False

    def test_forget(self, cache):
        cache.put("key", 1)
        cache.forget("key")
        assert cache.get("key") is None

    def test_flush_clears_everything(self, cache):
        cache.put("a", 1)
        cache.put("b", 2)
        cache.flush()
        assert cache.get("a") is None and cache.get("b") is None

    def test_expired_entries_are_gone(self, cache):
        cache.put("key", "value", ttl=1)
        time.sleep(1.1)
        assert cache.get("key") is None

    def test_unexpired_entries_survive(self, cache):
        cache.put("key", "value", ttl=60)
        assert cache.get("key") == "value"


class TestCacheApi:
    @pytest.fixture
    def cache(self):
        manager = CacheManager()
        manager._store = ArrayStore()
        return manager

    def test_remember_computes_once(self, cache):
        calls = []

        def compute():
            calls.append(1)
            return "computed"

        assert cache.remember("key", 60, compute) == "computed"
        assert cache.remember("key", 60, compute) == "computed"
        assert len(calls) == 1

    def test_remember_recomputes_after_expiry(self, cache):
        cache.remember("key", 1, lambda: "first")
        time.sleep(1.1)
        assert cache.remember("key", 60, lambda: "second") == "second"

    def test_forever_has_no_expiry(self, cache):
        cache.forever("key", "value")
        assert cache.get("key") == "value"

    def test_pull_returns_then_forgets(self, cache):
        cache.put("key", "value")
        assert cache.pull("key") == "value"
        assert cache.get("key") is None

    def test_increment_and_decrement(self, cache):
        assert cache.increment("counter") == 1
        assert cache.increment("counter", 5) == 6
        assert cache.decrement("counter", 2) == 4

    def test_increment_starts_from_zero(self, cache):
        assert cache.increment("fresh", 3) == 3

    def test_increment_preserves_the_ttl(self, cache):
        # increment() used to re-store via forever(), erasing the TTL.
        cache.put("counter", 1, ttl=60)
        cache.increment("counter")
        remaining = cache.store.expires_in("counter")
        assert remaining is not None and 0 < remaining <= 60

    def test_remember_caches_a_none_result(self, cache):
        calls = []

        def compute():
            calls.append(1)
            return None

        assert cache.remember("key", 60, compute) is None
        assert cache.remember("key", 60, compute) is None
        assert len(calls) == 1


class TestDriverResolution:
    def test_defaults_to_the_array_store(self):
        assert isinstance(CacheManager().store, ArrayStore)

    def test_file_driver_is_resolved_from_config(self, tmp_path):
        class FakeConfig:
            def get(self, key, default=None):
                return {"cache.default": "file"}.get(key, default)

        class FakeApp:
            base_path = str(tmp_path)

            def make(self, name):
                return FakeConfig()

        assert isinstance(CacheManager(FakeApp()).store, FileStore)

    def test_unreachable_redis_degrades_to_array(self, monkeypatch):
        class FakeConfig:
            def get(self, key, default=None):
                return {"cache.default": "redis"}.get(key, default)

        class FakeApp:
            base_path = "."

            def make(self, name):
                return FakeConfig()

        # No redis package / no server — must not raise.
        assert isinstance(CacheManager(FakeApp()).store, ArrayStore)
