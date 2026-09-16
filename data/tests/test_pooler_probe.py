"""statement_timeout is applied unconditionally; the pooler probe only warns."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import logging

import pytest

from craft.container.application import Container


@pytest.fixture
def pg_connection(migrated_database, is_postgres):
    if not is_postgres:
        pytest.skip("statement_timeout and the pooler probe are PostgreSQL-only")
    manager = Container.getInstance().make("db")
    return manager.write_connection


def test_statement_timeout_is_applied_when_configured(pg_connection):
    pg_connection.release()  # force a fresh checkout so the new config applies
    pg_connection.config["statement_timeout_ms"] = 5000
    try:
        pdo = pg_connection.pdo
        cursor = pdo.cursor()
        try:
            cursor.execute("SHOW statement_timeout")
            value = cursor.fetchone()[0]
        finally:
            cursor.close()
        assert value in ("5000", "5s", "5000ms")
    finally:
        pg_connection.config["statement_timeout_ms"] = 0
        pg_connection.release()


def test_statement_timeout_disabled_by_default_is_a_no_op(pg_connection):
    """0 (the default) means "don't touch it" - no SET statement is issued."""
    pg_connection.release()
    pg_connection.config["statement_timeout_ms"] = 0
    pdo = pg_connection.pdo  # must not raise
    assert pdo is not None
    pg_connection.release()


def test_pooler_probe_runs_at_most_once_per_process(pg_connection, caplog):
    """The probe is gated by a class-level flag; a second checkout skips it."""
    from craft.orm.connection import Connection

    original = Connection._pooler_probed
    Connection._pooler_probed = False
    pg_connection.release()  # force a fresh checkout so the probe actually runs
    try:
        with caplog.at_level(logging.WARNING, logger="craft"):
            _ = pg_connection.pdo
        assert Connection._pooler_probed is True
        # A second checkout must not probe again - no exception, no new work.
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="craft"):
            _ = pg_connection.pdo
        assert not any("transaction-mode pooler" in r.message for r in caplog.records)
    finally:
        Connection._pooler_probed = original
        pg_connection.release()


def test_pooler_probe_never_raises_even_if_the_query_fails(pg_connection):
    """Detection only - a probe failure must not break the checkout."""
    from craft.orm.connection import Connection

    original = Connection._pooler_probed
    Connection._pooler_probed = False
    try:
        # A closed pdo makes pg_backend_pid() fail; the probe must swallow it.
        broken = object()
        pg_connection._probe_pooler_mode(broken)  # must not raise
    finally:
        Connection._pooler_probed = original
