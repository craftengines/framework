"""A caught statement failure inside a transaction does not abort the transaction."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest

from craft.container.application import Container


@pytest.fixture
def db(migrated_database, is_postgres):
    if not is_postgres:
        pytest.skip("PostgreSQL aborts a transaction on any failed statement; SQLite does not")
    manager = Container.getInstance().make("db")
    manager.statement("DROP TABLE IF EXISTS savepoint_probe")
    manager.statement("CREATE TABLE savepoint_probe (code VARCHAR(10) PRIMARY KEY)")
    yield manager
    manager.statement("DROP TABLE IF EXISTS savepoint_probe")


def _insert_ignoring_duplicates(manager, code: str) -> None:
    try:
        manager.statement("INSERT INTO savepoint_probe (code) VALUES (?)", [code])
    except Exception as exc:  # noqa: BLE001 - asserting the driver's unique violation
        assert "duplicate" in str(exc).lower() or "unique" in str(exc).lower()


def test_work_after_a_caught_failure_is_committed(db) -> None:
    def work() -> None:
        _insert_ignoring_duplicates(db, "A")
        _insert_ignoring_duplicates(db, "A")
        _insert_ignoring_duplicates(db, "B")

    db.transaction(work)
    rows = db.statement("SELECT code FROM savepoint_probe ORDER BY code").fetchall()
    assert [row["code"] for row in rows] == ["A", "B"]


def test_a_select_inside_a_transaction_still_returns_its_rows(db) -> None:
    def work() -> list:
        db.statement("INSERT INTO savepoint_probe (code) VALUES (?)", ["C"])
        return db.statement("SELECT code FROM savepoint_probe").fetchall()

    assert [row["code"] for row in db.transaction(work)] == ["C"]


def test_an_uncaught_failure_still_rolls_everything_back(db) -> None:
    def work() -> None:
        db.statement("INSERT INTO savepoint_probe (code) VALUES (?)", ["D"])
        db.statement("INSERT INTO savepoint_probe (code) VALUES (?)", ["D"])

    with pytest.raises(Exception):  # noqa: B017 - any driver integrity error
        db.transaction(work)
    assert db.statement("SELECT code FROM savepoint_probe").fetchall() == []
