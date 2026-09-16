"""Pytest bootstrap for the Craft Framework test-suite.

By default the suite runs against an in-memory SQLite database whose schema is
built by the real migrator, so migrations are exercised on every run instead of
relying on hand-maintained fixture tables.

To validate the PostgreSQL dialect, point the suite at a real server::

    $env:CRAFT_TEST_DB = "pgsql"
    $env:DB_HOST = "127.0.0.1"; $env:DB_PORT = "5499"
    $env:DB_DATABASE = "craft_test"   # must be disposable (NR-02)
    $env:DB_USERNAME = "craft"; $env:DB_PASSWORD = "secretpassword"
    python -m pytest

Per-agent test databases: parallel pytest workers derive a unique DB name from
the worker id, ensuring zero collisions. The DB name always ends in `_test` so
`is_disposable_database()` (Slice 0) accepts it.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import hashlib
import os
import sys
import uuid
from typing import Any, Generator

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Must be set before `bootstrap.app` builds the config repository.
os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("QUEUE_CONNECTION", "sync")
os.environ.setdefault("CACHE_DRIVER", "array")

TEST_DB = os.environ.get("CRAFT_TEST_DB", "sqlite").lower()
os.environ["DB_CONNECTION"] = TEST_DB

# Per-agent database naming for parallel workers.
_WORKER_ID = os.environ.get("PYTEST_XDIST_WORKER", "master")
if TEST_DB == "sqlite":
    os.environ["DB_DATABASE"] = ":memory:"
else:
    # Derive per-worker DB name, always ending in _test.
    base_name = os.environ.get("DB_DATABASE", "craft_test")
    if not base_name.endswith("_test"):
        base_name = f"{base_name}_test"
    if _WORKER_ID != "master":
        # Append worker id to avoid collisions in parallel runs.
        base_name = f"{base_name}_{_WORKER_ID}"
    os.environ["DB_DATABASE"] = base_name

import engine  # noqa: F401,E402  installs the `craft.*` import alias

# Refuse to run tests on a permanent database (dev DB accidentally run as test).
from engine.migrations.safety import is_disposable_database as _is_disposable_db


def _check_database_safety() -> None:
    """Raise if the test database is not disposable, preventing accidental data loss."""
    if TEST_DB == "sqlite":
        # SQLite in-memory (:memory:) is always disposable.
        return
    driver = TEST_DB
    database = os.environ.get("DB_DATABASE", "")
    if not _is_disposable_db(driver, database):
        pytest.exit(
            f"REFUSE: test database '{database}' is not disposable (missing _test suffix or allowlist). "
            f"This safety check prevents wiping a permanent database. "
            f"Use a database ending in '_test' or add it to DB_DISPOSABLE_DATABASES."
        )


_check_database_safety()


@pytest.fixture
def is_postgres() -> bool:
    """Return whether tests are running against PostgreSQL."""
    return TEST_DB in ("pgsql", "postgres", "postgresql")


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> Generator[Any, None, None]:
    """Build the test schema with the real migrator, once per session.

    For PostgreSQL, acquires an advisory lock to coordinate parallel pytest
    workers (pytest-xdist) so schema mutations do not race.
    """
    from bootstrap.app import app
    from craft.migrations.migrator import Migrator

    is_pg = TEST_DB in ("pgsql", "postgres", "postgresql")
    lock_id = None

    try:
        # Acquire lock for parallel-safe schema mutation on PostgreSQL.
        if is_pg:
            db = app.make("db")
            lock_id = int(
                hashlib.md5(os.environ.get("DB_DATABASE", "craft_test").encode()).hexdigest()[:8],
                16
            )
            db.select_raw(f"SELECT pg_advisory_lock({lock_id})").first()

        migrator = Migrator(app)
        if TEST_DB != "sqlite":
            # A real server keeps state between runs — start from a clean schema.
            migrator.drop_all_tables()
        migrator.run()
        yield app

    finally:
        # Release the advisory lock if it was acquired.
        if is_pg and lock_id is not None:
            try:
                db = app.make("db")
                db.select_raw(f"SELECT pg_advisory_unlock({lock_id})").first()
            except Exception:
                pass  # Lock already released or connection closed; no error needed.


@pytest.fixture
def two_tenants(migrated_database) -> Generator[tuple[str, str], None, None]:
    """Create two test tenant records and return their IDs.

    Yields:
        A tuple of (tenant_a_id, tenant_b_id), two UUIDs for distinct tenants.

    Cleans up both tenants after the test.
    """
    from craft.facades import DB

    tenant_a_id = str(uuid.uuid4())
    tenant_b_id = str(uuid.uuid4())

    # Insert both tenants into the database (is_active defaults to True).
    DB.table("tenants").insert({"id": tenant_a_id})
    DB.table("tenants").insert({"id": tenant_b_id})

    yield tenant_a_id, tenant_b_id

    # Clean up.
    DB.table("tenants").where_in("id", [tenant_a_id, tenant_b_id]).delete()


@pytest.fixture
def client_for_host(migrated_database):
    """Return a test client factory that sets the Host header.

    Returns:
        A callable that takes a hostname string and returns a TestClient
        with the Host header pre-set, for testing ScopeTenant.resolve()
        and host-based tenant resolution end-to-end.
    """
    from starlette.testclient import TestClient
    from bootstrap.app import asgi_app

    def _make_client(host: str) -> TestClient:
        """Create a TestClient with a specific Host header."""
        client = TestClient(asgi_app)
        client.headers["Host"] = host
        return client

    return _make_client


@pytest.fixture
def unprivileged_postgres_role(migrated_database, is_postgres) -> Generator[str, None, None]:
    """Create a PostgreSQL role without BYPASSRLS for testing RLS enforcement.

    Yields:
        The role name (username).

    On SQLite, this is a no-op — the fixture yields a dummy value.
    """
    if not is_postgres:
        yield "sqlite_unprivileged"
        return

    from craft.facades import DB

    role_name = f"craft_unprivileged_{_WORKER_ID}_{os.getpid()}"

    try:
        # Drop the role if it already exists (from a previous run).
        DB.select_raw(f"DROP ROLE IF EXISTS {role_name}").first()
    except Exception:
        pass

    # Create a new role without superuser or BYPASSRLS privileges.
    try:
        DB.select_raw(f"CREATE ROLE {role_name} WITH LOGIN PASSWORD 'test'").first()
    except Exception as e:
        pytest.skip(f"Cannot create PostgreSQL role for unprivileged testing: {e}")

    yield role_name

    # Clean up.
    try:
        DB.select_raw(f"DROP ROLE IF EXISTS {role_name}").first()
    except Exception:
        pass  # Role already dropped or owned by other sessions; ignore.
