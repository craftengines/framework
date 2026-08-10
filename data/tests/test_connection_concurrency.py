"""One physical session per thread — the prerequisite for serving in parallel.

A `Connection` used to hold a single raw DB-API connection plus mutable
per-request state (transaction depth, tenant schema). That is only safe while
the process handles one request at a time, which is exactly the throughput
ceiling this design removes. These tests assert the isolation directly, because
the failure mode under load — two threads sharing a cursor, or one tenant's
request repointing another tenant's `search_path` — does not show up in a
single-threaded run at all.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import threading

import pytest

from craft.orm.connection import Connection


@pytest.fixture
def file_connection(tmp_path):
    """A file-backed SQLite connection — the per-thread mode.

    `:memory:` is deliberately the exception (one shared session), so it cannot
    be used to test the per-thread behaviour.
    """
    conn = Connection({"driver": "sqlite", "database": str(tmp_path / "concurrency.sqlite")})
    conn.statement("CREATE TABLE widgets (id INTEGER PRIMARY KEY, name TEXT)")
    yield conn
    conn.close()


def _run_in_threads(target, count=4):
    """Run `target(index)` in `count` threads, re-raising anything they raise."""
    errors = []
    results = [None] * count

    def wrapper(i):
        try:
            results[i] = target(i)
        except Exception as exc:  # pragma: no cover - only on failure
            errors.append(exc)

    threads = [threading.Thread(target=wrapper, args=(i,)) for i in range(count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    if errors:
        raise errors[0]
    return results


class TestSessionPerThread:
    def test_each_thread_opens_its_own_connection(self, file_connection):
        def query(i):
            file_connection.statement("SELECT 1")
            return id(file_connection._session())

        session_ids = _run_in_threads(query, count=4)

        assert len(set(session_ids)) == 4, "threads shared a session"
        # 4 worker threads + the main thread, which created the table.
        assert file_connection.open_sessions == 5

    def test_transaction_depth_is_not_shared(self, file_connection):
        """One thread inside a transaction must not make another thread think
        it is inside one — `DatabaseManager` routes reads on exactly that flag,
        and `statement()` decides whether to commit on it."""
        inside = threading.Event()
        checked = threading.Event()
        observed = {}

        def holder():
            file_connection.begin()
            inside.set()
            checked.wait(timeout=10)
            file_connection.rollback()

        def observer():
            inside.wait(timeout=10)
            observed["depth"] = file_connection._in_transaction
            checked.set()

        threads = [threading.Thread(target=holder), threading.Thread(target=observer)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert observed["depth"] == 0

    def test_concurrent_writes_all_land(self, file_connection):
        """The real regression: parallel statements on one Connection used to
        share a cursor, losing or interleaving results."""

        def write(i):
            for n in range(10):
                file_connection.statement(
                    "INSERT INTO widgets (name) VALUES (?)", [f"t{i}-{n}"]
                )
            return True

        _run_in_threads(write, count=4)

        rows = file_connection.statement("SELECT COUNT(*) AS n FROM widgets").fetchone()
        assert rows["n"] == 40

    def test_close_shuts_down_every_thread_session(self, file_connection):
        _run_in_threads(lambda i: file_connection.statement("SELECT 1"), count=3)
        assert file_connection.open_sessions == 4   # 3 threads + main

        file_connection.close()
        assert file_connection.open_sessions == 0

        # Still usable afterwards — close is not a one-way door.
        file_connection.statement("SELECT 1")
        assert file_connection.open_sessions == 1


class TestPoolIsBounded:
    """Per-thread connections that are never given back are not a pool: they
    accumulate one per thread until the database answers "too many clients
    already". `release()` is the request boundary that makes it one."""

    def test_release_returns_the_connection_for_reuse(self, file_connection):
        file_connection.statement("SELECT 1")
        assert file_connection.pool_stats == {"open": 1, "idle": 0}

        file_connection.release()
        assert file_connection.pool_stats == {"open": 1, "idle": 1}

        # The next use borrows the same physical connection instead of opening
        # a second one.
        file_connection.statement("SELECT 1")
        assert file_connection.pool_stats == {"open": 1, "idle": 0}

    def test_threads_that_release_reuse_a_small_pool(self, tmp_path):
        conn = Connection({
            "driver": "sqlite",
            "database": str(tmp_path / "pool.sqlite"),
            "pool_size": 2,
        })
        try:
            conn.statement("CREATE TABLE t (id INTEGER PRIMARY KEY)")
            conn.release()

            def work(i):
                for _ in range(5):
                    conn.statement("SELECT 1")
                conn.release()
                return True

            _run_in_threads(work, count=8)
            assert conn.pool_stats["open"] <= 2
        finally:
            conn.close()

    def test_exhaustion_raises_instead_of_hanging(self, tmp_path):
        conn = Connection({
            "driver": "sqlite",
            "database": str(tmp_path / "tiny.sqlite"),
            "pool_size": 1,
            "pool_timeout": 0.2,
        })
        try:
            conn.statement("SELECT 1")   # main thread holds the only connection

            def borrow(i):
                conn.statement("SELECT 1")

            with pytest.raises(Exception) as excinfo:
                _run_in_threads(borrow, count=1)
            assert "pool_size" in str(excinfo.value)
        finally:
            conn.close()

    def test_release_rolls_back_an_abandoned_transaction(self, file_connection):
        """A request that opens a transaction and never closes it must not hand
        its uncommitted work to whoever borrows the connection next."""
        file_connection.statement("INSERT INTO widgets (name) VALUES ('kept')")
        file_connection.begin()
        file_connection.statement("INSERT INTO widgets (name) VALUES ('abandoned')")
        file_connection.release()

        assert file_connection._in_transaction == 0
        rows = file_connection.statement(
            "SELECT name FROM widgets ORDER BY id"
        ).fetchall()
        assert [r["name"] for r in rows] == ["kept"]


class TestInMemorySqliteSharesOneSession:
    """An in-memory database exists only inside the connection that created it,
    so per-thread sessions would hand each thread a different empty database.
    This is the one documented exception."""

    def test_threads_share_the_session_and_therefore_the_data(self):
        conn = Connection({"driver": "sqlite", "database": ":memory:"})
        try:
            conn.statement("CREATE TABLE t (id INTEGER PRIMARY KEY)")
            session_ids = _run_in_threads(
                lambda i: id(conn._session()) or conn.statement("SELECT 1") and id(conn._session()),
                count=3,
            )
            assert len(set(session_ids)) == 1
            assert conn.open_sessions == 1
            # The table created on the main thread is visible from the others.
            _run_in_threads(lambda i: conn.statement("SELECT * FROM t"), count=3)
        finally:
            conn.close()


class TestTenantSchemaIsPerThread:
    """`use_schema()` is per-thread because the tenant is per-request. Were it
    process-wide, one tenant's request could repoint `search_path` while
    another tenant's request was mid-query — a cross-tenant read."""

    def test_two_threads_hold_different_schemas(self, is_postgres, migrated_database):
        if not is_postgres:
            pytest.skip("search_path isolation only exists on PostgreSQL")

        connection = migrated_database.make("db").write_connection
        connection.statement('CREATE SCHEMA IF NOT EXISTS tenant_alpha')
        connection.statement('CREATE SCHEMA IF NOT EXISTS tenant_beta')

        seen = {}
        ready = threading.Barrier(2, timeout=30)

        def use(name):
            connection.use_schema(name)
            ready.wait()   # both threads have set their schema before reading
            row = connection.statement("SELECT current_schema() AS s").fetchone()
            seen[name] = row["s"]

        threads = [
            threading.Thread(target=use, args=("tenant_alpha",)),
            threading.Thread(target=use, args=("tenant_beta",)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)

        assert seen == {"tenant_alpha": "tenant_alpha", "tenant_beta": "tenant_beta"}

    def test_schema_reports_the_calling_thread(self, file_connection):
        file_connection.use_schema(None)
        assert file_connection.schema is None


class TestAuthStateIsPerThread:
    """`AuthManager` is a container singleton, but "the current user" belongs to
    the request. With requests served on a thread pool, instance state would let
    one visitor's identity be read — or overwritten — by another's request."""

    def test_a_login_in_one_thread_is_invisible_to_another(self, migrated_database):
        auth = migrated_database.make("auth")

        class FakeUser:
            def __init__(self, uid):
                self.uid = uid

            def get_attribute(self, name):
                return self.uid if name == "id" else None

        seen = {}
        ready = threading.Barrier(3, timeout=30)

        def as_user(uid):
            auth.set_user(FakeUser(uid))
            ready.wait()          # everyone is logged in before anyone looks
            seen[uid] = auth.id()

        def as_guest():
            ready.wait()
            seen["guest"] = (auth.check(), auth.user())

        threads = [
            threading.Thread(target=as_user, args=(1,)),
            threading.Thread(target=as_user, args=(2,)),
            threading.Thread(target=as_guest),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)

        assert seen[1] == 1 and seen[2] == 2
        assert seen["guest"] == (False, None), "a logged-in user leaked across threads"
