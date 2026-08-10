"""Module state must not cost a SELECT per request.

Every route declared with `.module(...)` asked the database whether the module
was enabled, on every single request, with no cache. These tests count the SQL
actually issued — asserting only on the answer would pass just as happily with
the uncached version, which is the regression being prevented.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest

from craft.modules.manager import ModuleManager


class ModuleQueryCounter:
    """Counts SELECTs issued against the `modules` table."""

    def __init__(self, db):
        self.db = db
        self.queries = []
        self._original = db.statement

    def __enter__(self):
        def counting(query, bindings=None, read=False):
            if "modules" in query.lower() and query.lstrip().upper().startswith("SELECT"):
                self.queries.append(query)
            return self._original(query, bindings, read)

        self.db.statement = counting
        return self

    def __exit__(self, *exc):
        self.db.statement = self._original
        return False

    @property
    def count(self) -> int:
        return len(self.queries)


@pytest.fixture
def counter(migrated_database):
    return lambda: ModuleQueryCounter(migrated_database.make("db"))


@pytest.fixture
def manager(migrated_database):
    mgr = ModuleManager()
    mgr.register("inventory", "Inventory")
    return mgr


class TestModuleStateCache:
    def test_repeated_lookups_hit_the_database_once(self, manager, counter):
        with counter() as c:
            for _ in range(10):
                manager.is_enabled("inventory")
            assert c.count == 1

    def test_disable_invalidates_the_cache_immediately(self, manager):
        assert manager.is_enabled("inventory") is True
        manager.disable("inventory")
        assert manager.is_enabled("inventory") is False
        manager.enable("inventory")
        assert manager.is_enabled("inventory") is True

    def test_forget_cached_state_forces_a_fresh_read(self, manager, counter):
        with counter() as c:
            manager.is_enabled("inventory")
            manager.forget_cached_state("inventory")
            manager.is_enabled("inventory")
            assert c.count == 2

    def test_expired_entries_are_re_read(self, manager, counter):
        manager.cache_ttl = 0
        with counter() as c:
            manager.is_enabled("inventory")
            manager.is_enabled("inventory")
            assert c.count == 2

    def test_unknown_module_reports_none_not_false(self, manager):
        """`None` lets the router fall back to config; `False` would 404 it."""
        assert manager.state("never-heard-of-it") is None
        assert manager.is_enabled("never-heard-of-it") is False
