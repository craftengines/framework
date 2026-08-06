"""Pytest bootstrap for the Codepy Framework test-suite.

By default the suite runs against an in-memory SQLite database whose schema is
built by the real migrator, so migrations are exercised on every run instead of
relying on hand-maintained fixture tables.

To validate the PostgreSQL dialect, point the suite at a real server::

    $env:CODEPY_TEST_DB = "pgsql"
    $env:DB_HOST = "127.0.0.1"; $env:DB_PORT = "5499"
    $env:DB_DATABASE = "codepy_validation"
    $env:DB_USERNAME = "codepy"; $env:DB_PASSWORD = "secretpassword"
    python -m pytest
"""
# Codepy Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Must be set before `bootstrap.app` builds the config repository.
os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("QUEUE_CONNECTION", "sync")
os.environ.setdefault("CACHE_DRIVER", "array")

TEST_DB = os.environ.get("CODEPY_TEST_DB", "sqlite").lower()
os.environ["DB_CONNECTION"] = TEST_DB
if TEST_DB == "sqlite":
    os.environ["DB_DATABASE"] = ":memory:"

import services  # noqa: F401,E402  installs the `codepy.*` import alias


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    """Build the test schema with the real migrator, once per session."""
    from bootstrap.app import app
    from services.migrations.migrator import Migrator

    migrator = Migrator(app)
    if TEST_DB != "sqlite":
        # A real server keeps state between runs — start from a clean schema.
        migrator.drop_all_tables()
    migrator.run()
    yield app


@pytest.fixture
def is_postgres():
    return TEST_DB in ("pgsql", "postgres", "postgresql")
