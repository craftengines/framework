"""Tests for distributed locks and the atomic cache primitive behind them.

Phase 4 of the PostgreSQL-native data layer. Advisory locks need PostgreSQL, so
the exclusivity assertions run against whichever mechanism the active driver
actually has — the lock on PostgreSQL, `Cache.add()` everywhere else. Both are
required to hold, because the scheduler falls back to the second one.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import threading

import pytest

from craft.cache.manager import ArrayStore, CacheManager, FileStore
from craft.orm.dialect import UnsupportedFeatureError
from craft.orm.locks import LockManager, key_to_bigint
from craft.schedule.manager import ScheduleManager


# -- key hashing ---------------------------------------------------------------


def test_a_key_hashes_to_a_signed_64_bit_integer():
    value = key_to_bigint("invoices:close:2026-08")
    assert -(2 ** 63) <= value < 2 ** 63


def test_hashing_is_stable_and_distinguishing():
    assert key_to_bigint("a") == key_to_bigint("a")
    assert key_to_bigint("a") != key_to_bigint("b")
    # Long structured keys must not collapse onto each other.
    prefix = "tenant:11111111-1111-1111-1111-111111111111:invoices:"
    assert key_to_bigint(prefix + "close") != key_to_bigint(prefix + "open")


def test_an_empty_key_is_refused():
    with pytest.raises(ValueError):
        key_to_bigint("")


def test_explain_reports_the_integer_for_a_suspected_collision(migrated_database):
    report = LockManager(migrated_database).explain("reports:nightly")
    assert report["key"] == "reports:nightly"
    assert report["id"] == key_to_bigint("reports:nightly")
    assert isinstance(report["holders"], list)


# -- capability gating ---------------------------------------------------------


def test_supported_matches_the_dialect(migrated_database):
    manager = LockManager(migrated_database)
    assert manager.supported() is migrated_database.make("db").dialect.supports(
        "advisory_locks"
    )


def test_a_driver_without_advisory_locks_refuses_rather_than_pretending(migrated_database):
    manager = LockManager(migrated_database)
    if manager.supported():
        pytest.skip("this driver has advisory locks; the refusal path needs one without")

    with pytest.raises(UnsupportedFeatureError):
        manager.key("anything").acquire()

    with pytest.raises(UnsupportedFeatureError):
        with manager.transaction("anything"):
            pass


def test_block_for_requires_a_positive_wait(migrated_database):
    with pytest.raises(ValueError):
        LockManager(migrated_database).key("x").block_for(0)


# -- exclusivity ---------------------------------------------------------------


def test_only_one_caller_runs_under_a_lock(migrated_database):
    """Exactly one callback runs; the loser gets None, not an exception."""
    manager = LockManager(migrated_database)
    if not manager.supported():
        pytest.skip("advisory locks are not available on this driver")

    ran = []
    started = threading.Event()
    proceed = threading.Event()

    def slow():
        started.set()
        proceed.wait(timeout=5)
        ran.append("winner")
        return "done"

    holder = threading.Thread(target=lambda: manager.key("phase4:excl").get(slow))
    holder.start()
    started.wait(timeout=5)

    assert manager.key("phase4:excl").get(lambda: ran.append("loser")) is None

    proceed.set()
    holder.join(timeout=10)
    assert ran == ["winner"]


def test_a_lock_is_released_when_the_callback_raises(migrated_database):
    manager = LockManager(migrated_database)
    if not manager.supported():
        pytest.skip("advisory locks are not available on this driver")

    def explode():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        manager.key("phase4:raise").get(explode)

    # Free again: a lock stranded by an exception is the failure mode a TTL
    # cannot rule out and a `finally` can.
    assert manager.key("phase4:raise").get(lambda: "second") == "second"


# -- the atomic cache primitive ------------------------------------------------


@pytest.mark.parametrize("store_factory", [
    lambda tmp: ArrayStore(),
    lambda tmp: FileStore(str(tmp)),
])
def test_add_is_put_if_absent(store_factory, tmp_path):
    store = store_factory(tmp_path)

    assert store.add("k", "1", 60) is True
    assert store.add("k", "2", 60) is False
    assert store.get("k") == "1"

    store.forget("k")
    assert store.add("k", "3", 60) is True


@pytest.mark.parametrize("store_factory", [
    lambda tmp: ArrayStore(),
    lambda tmp: FileStore(str(tmp)),
])
def test_an_expired_entry_does_not_block_the_key_forever(store_factory, tmp_path):
    import time

    store = store_factory(tmp_path)
    store.add("k", "1", 1)
    time.sleep(1.1)
    assert store.add("k", "2", 60) is True
    assert store.get("k") == "2"


def test_exactly_one_thread_wins_add():
    """The race `has()` + `put()` loses and `add()` wins."""
    store = ArrayStore()
    winners = []
    barrier = threading.Barrier(12)

    def contend():
        barrier.wait()
        if store.add("only-one", "x", 60):
            winners.append(threading.current_thread().name)

    threads = [threading.Thread(target=contend) for _ in range(12)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert len(winners) == 1


def test_the_manager_exposes_add():
    cache = CacheManager()
    assert cache.add("phase4:add", "1", 60) is True
    assert cache.add("phase4:add", "2", 60) is False
    cache.forget("phase4:add")


# -- scheduler integration -----------------------------------------------------


def test_without_overlapping_lets_only_one_run_through(migrated_database):
    manager = ScheduleManager(migrated_database)
    runs = []
    task = manager.call(lambda: runs.append("ran")).without_overlapping(5)

    assert task.run() is not None or runs == ["ran"]
    assert runs == ["ran"]


def test_a_held_overlap_lock_skips_the_run(migrated_database):
    """A run started elsewhere while this one is due does nothing here.

    The lock has to be taken on a *different* connection. Advisory locks are
    re-entrant within one session — a backend that holds a lock is granted it
    again — so holding and testing on the same connection would prove nothing
    and pass for the wrong reason. Overlap protection is between processes,
    which is what it is for.
    """
    manager = ScheduleManager(migrated_database)
    lock = manager.lock()

    runs = []
    task = manager.call(lambda: runs.append("ran")).without_overlapping(5)

    if lock is not None and lock.supported():
        other = LockManager(_SecondConnection(migrated_database))
        held = other.key(task.lock_key).acquire()
        assert held, "could not take the lock on the second connection"
        try:
            assert task.run() is None
        finally:
            other.key(task.lock_key).release()
    else:
        cache = manager.cache()
        assert cache.add(task.lock_key, "1", 300) is True
        try:
            assert task.run() is None
        finally:
            cache.forget(task.lock_key)

    assert runs == []


class _SecondConnection:
    """Container shim handing out a database manager of its own.

    A second `DatabaseManager` built from the same config opens its own
    physical connection, which is what makes it a different lock holder.
    """

    def __init__(self, app):
        from craft.orm.db import DatabaseManager

        self._app = app
        self._db = DatabaseManager(app)
        self._db.boot()

    def make(self, key):
        return self._db if key == "db" else self._app.make(key)


def test_the_overlap_lock_is_freed_after_the_run(migrated_database):
    manager = ScheduleManager(migrated_database)
    runs = []
    task = manager.call(lambda: runs.append(len(runs))).without_overlapping(5)

    task.run()
    task.run()
    assert runs == [0, 1], "the lock was not released between runs"


def test_a_task_without_the_option_never_takes_a_lock(migrated_database):
    manager = ScheduleManager(migrated_database)
    runs = []
    task = manager.call(lambda: runs.append("ran"))

    task.run()
    task.run()
    assert runs == ["ran", "ran"]
