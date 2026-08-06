"""Connection layer: placeholder translation and row access."""

import pytest

from services.orm.connection import Connection, Row, normalize_placeholders


class TestPlaceholderNormalization:
    def test_sqlite_passes_through_untouched(self):
        sql, params = normalize_placeholders(
            "SELECT * FROM users WHERE id = ?", [1], "qmark"
        )
        assert sql == "SELECT * FROM users WHERE id = ?"
        assert params == [1]

    def test_positional_becomes_percent_s_for_postgres(self):
        sql, params = normalize_placeholders(
            "SELECT * FROM users WHERE id = ? AND active = ?", [1, True], "pyformat"
        )
        assert sql == "SELECT * FROM users WHERE id = %s AND active = %s"
        assert params == [1, True]

    def test_named_becomes_pyformat_for_postgres(self):
        sql, params = normalize_placeholders(
            "INSERT INTO users (id, name) VALUES (:id, :name)",
            {"id": 1, "name": "Jane"},
            "pyformat",
        )
        assert sql == "INSERT INTO users (id, name) VALUES (%(id)s, %(name)s)"
        assert params == {"id": 1, "name": "Jane"}

    def test_question_marks_inside_string_literals_are_not_rewritten(self):
        sql, _ = normalize_placeholders(
            "SELECT * FROM t WHERE label = 'why?' AND id = ?", [1], "pyformat"
        )
        assert sql == "SELECT * FROM t WHERE label = 'why?' AND id = %s"

    def test_colon_names_inside_string_literals_are_not_rewritten(self):
        sql, _ = normalize_placeholders(
            "SELECT * FROM t WHERE url = 'https://x' AND id = :id", {"id": 1}, "pyformat"
        )
        assert "'https://x'" in sql
        assert "%(id)s" in sql

    def test_postgres_casts_are_not_mistaken_for_placeholders(self):
        sql, _ = normalize_placeholders(
            "SELECT id::text FROM users WHERE id = :id", {"id": 1}, "pyformat"
        )
        assert "id::text" in sql
        assert "%(id)s" in sql

    def test_none_bindings_produce_an_empty_list(self):
        _, params = normalize_placeholders("SELECT 1", None, "pyformat")
        assert params == []


class TestRow:
    def test_supports_attribute_key_and_positional_access(self):
        row = Row({"id": 7, "name": "Jane"})
        assert row.id == 7
        assert row["name"] == "Jane"
        assert row[0] == 7

    def test_converts_to_dict(self):
        assert dict(Row({"a": 1, "b": 2})) == {"a": 1, "b": 2}

    def test_unknown_attribute_raises(self):
        with pytest.raises(AttributeError):
            Row({"id": 1}).missing

    def test_get_returns_default(self):
        assert Row({"id": 1}).get("nope", "fallback") == "fallback"


class TestSqliteConnection:
    @pytest.fixture
    def connection(self):
        conn = Connection({"driver": "sqlite", "database": ":memory:"})
        conn.statement("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT)")
        return conn

    def test_driver_and_paramstyle(self, connection):
        assert connection.driver == "sqlite"
        assert connection.paramstyle == "qmark"

    def test_insert_and_select_roundtrip(self, connection):
        connection.statement("INSERT INTO t (name) VALUES (?)", ["Jane"])
        rows = connection.statement("SELECT * FROM t").fetchall()
        assert len(rows) == 1
        assert rows[0].name == "Jane"

    def test_named_bindings_work_on_sqlite(self, connection):
        connection.statement("INSERT INTO t (name) VALUES (:name)", {"name": "Bob"})
        assert connection.statement("SELECT * FROM t").fetchone().name == "Bob"

    def test_table_exists(self, connection):
        assert connection.table_exists("t") is True
        assert connection.table_exists("nope") is False

    def test_rollback_discards_the_transaction(self, connection):
        connection.begin()
        connection.statement("INSERT INTO t (name) VALUES (?)", ["ghost"])
        connection.rollback()
        assert len(connection.statement("SELECT * FROM t").fetchall()) == 0

    def test_commit_persists_the_transaction(self, connection):
        connection.begin()
        connection.statement("INSERT INTO t (name) VALUES (?)", ["kept"])
        connection.commit()
        assert len(connection.statement("SELECT * FROM t").fetchall()) == 1

    def test_pgsql_alias_normalises_to_postgresql(self):
        assert Connection({"driver": "pgsql"}).driver == "postgresql"
