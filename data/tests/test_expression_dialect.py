"""Tests for the expression seam and the dialect capability layer.

Phase 1 of the PostgreSQL-native data layer: `Expr` is the only sanctioned way
past the query builder's identifier and operator allowlists, and `Dialect` is
the only place that answers "can this driver do X?".
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest

from craft.orm.dialect import (
    FEATURES,
    MySqlDialect,
    PostgresDialect,
    SqliteDialect,
    UnsupportedFeatureError,
    dialect_for,
)
from craft.orm.expression import Expr, Raw
from craft.orm.query_builder import QueryBuilder


# -- Expr ----------------------------------------------------------------------


def test_expr_counts_its_placeholders():
    expr = Expr("meta @> ?::jsonb", ['{"a":1}'])
    assert expr.sql == "meta @> ?::jsonb"
    assert expr.bindings == ['{"a":1}']


def test_expr_rejects_a_binding_count_mismatch():
    with pytest.raises(ValueError, match="placeholder"):
        Expr("a = ? AND b = ?", ["only-one"])


def test_expr_rejects_an_empty_fragment():
    with pytest.raises(ValueError):
        Expr("   ")


def test_raw_is_a_ddl_snippet_not_a_value():
    assert str(Raw("gen_random_uuid()")) == "gen_random_uuid()"
    with pytest.raises(ValueError):
        Raw("")


# -- builder integration -------------------------------------------------------


def test_where_expr_compiles_into_the_where_clause():
    qb = QueryBuilder(table_name="accounts", db=object())
    qb.where("active", True).where_expr(Expr("meta @> ?::jsonb", ['{"plan":"pro"}']))
    sql, params = qb.to_sql()

    assert "WHERE active = ? AND meta @> ?::jsonb" in sql
    assert params == [True, '{"plan":"pro"}']


def test_where_expr_refuses_a_bare_string():
    qb = QueryBuilder(table_name="accounts", db=object())
    with pytest.raises(TypeError):
        qb.where_expr("meta @> '{}'::jsonb")


def test_select_expr_widens_a_star_and_binds_first():
    qb = QueryBuilder(table_name="documents", db=object())
    qb.select_expr(Expr("embedding <=> ?::vector", ["[1,2]"]), "distance")
    qb.where("kind", "note")
    sql, params = qb.to_sql()

    # The row itself survives, and the computed column follows it.
    assert sql.startswith("SELECT documents.*, embedding <=> ?::vector AS distance")
    # Select bindings come before where bindings — positional rewriting for the
    # format paramstyle depends on it.
    assert params == ["[1,2]", "note"]


def test_order_by_expr_binds_last():
    qb = QueryBuilder(table_name="articles", db=object())
    qb.where("published", True)
    qb.order_by("id")
    qb.order_by_expr(Expr("ts_rank_cd(doc, ?)", ["queue"]), "desc")
    sql, params = qb.to_sql()

    assert "ORDER BY id ASC, ts_rank_cd(doc, ?) DESC" in sql
    assert params == [True, "queue"]


def test_or_where_expr_keeps_earlier_ands_grouped():
    qb = QueryBuilder(table_name="notes", db=object())
    qb.where("deleted_at", "IS", "NULL_SENTINEL")
    qb.or_where_expr(Expr("tags && ?", [["a"]]))
    sql, _ = qb.to_sql()

    assert "(deleted_at IS ?) OR tags && ?" in sql


def test_expression_clauses_are_dropped_from_an_aggregate():
    """A COUNT(*) must not carry the select/order fragments or their bindings."""
    recorded = {}

    class _Db:
        driver = "sqlite"

        def statement(self, query, params=None, read=False):
            recorded["query"], recorded["params"] = query, params

            class _Result:
                def fetchone(self_inner):
                    return {"aggregate": 7}

            return _Result()

    qb = QueryBuilder(table_name="documents", db=_Db())
    qb.select_expr(Expr("embedding <=> ?::vector", ["[1,2]"]), "distance")
    qb.order_by_expr(Expr("embedding <=> ?::vector", ["[1,2]"]), "asc")
    qb.where("kind", "note")

    assert qb.count() == 7
    assert "distance" not in recorded["query"]
    assert "ORDER BY" not in recorded["query"]
    assert recorded["params"] == ["note"]

    # The builder is restored, so the aggregate is not destructive.
    sql, params = qb.to_sql()
    assert "AS distance" in sql
    assert params == ["[1,2]", "note", "[1,2]"]


# -- dialects ------------------------------------------------------------------


def test_postgres_supports_everything_the_framework_asks_about():
    dialect = PostgresDialect()
    assert all(dialect.supports(feature) for feature in FEATURES)


def test_sqlite_refuses_the_postgres_capabilities():
    dialect = SqliteDialect()
    assert not dialect.supports("rls")
    assert not dialect.supports("jsonb")
    assert dialect.supports("transactional_ddl")


def test_require_raises_and_names_the_way_out():
    with pytest.raises(UnsupportedFeatureError) as excinfo:
        SqliteDialect().require("rls", "isolates one tenant's rows from another's")

    message = str(excinfo.value)
    assert "'sqlite'" in message
    assert "'rls'" in message
    assert "PostgreSQL" in message


def test_require_is_a_no_op_when_supported():
    assert PostgresDialect().require("skip_locked", "backs the queue") is None


def test_an_unknown_capability_is_a_typo_not_an_answer():
    with pytest.raises(ValueError, match="Unknown capability"):
        PostgresDialect().supports("skiplocked")


def test_an_unprobed_dialect_reports_everything():
    """No connection to ask means "compile it" — the answer for unit tests."""
    dialect = PostgresDialect()
    assert dialect.version is None
    assert dialect.supports("uuidv7") is True
    assert dialect.version_advice() is None


def test_a_probed_dialect_gates_on_the_server_version():
    from craft.orm.dialect import RECOMMENDED_POSTGRES

    old = PostgresDialect(extensions=set(), version=(15, 18))
    assert old.supports("uuidv7") is False, "uuidv7() arrived in PostgreSQL 18"
    assert old.supports("skip_locked") is True, "core features are unaffected"
    assert old.meets_minimum is True
    assert old.meets_recommended is False

    current = PostgresDialect(extensions=set(), version=RECOMMENDED_POSTGRES)
    assert current.supports("uuidv7") is True
    assert current.meets_recommended is True
    assert current.version_advice() is None


def test_the_advice_distinguishes_unsupported_from_merely_old():
    below_minimum = PostgresDialect(extensions=set(), version=(12, 0))
    assert below_minimum.meets_minimum is False
    assert "below the minimum" in below_minimum.version_advice()

    supported = PostgresDialect(extensions=set(), version=(15, 18))
    advice = supported.version_advice()
    assert "works" in advice
    assert "uuidv7" in advice, "the advice must name what is missing"


def test_a_version_gated_refusal_names_the_version_not_the_extension():
    old = PostgresDialect(extensions=set(), version=(15, 18))
    with pytest.raises(UnsupportedFeatureError) as excinfo:
        old.require("uuidv7", "generates time-ordered keys in the database")

    message = str(excinfo.value)
    assert "18" in message and "15.18" in message
    assert "CREATE EXTENSION" not in message


def test_an_extension_gated_refusal_names_the_extension():
    dialect = PostgresDialect(extensions=set(), version=(18, 4))
    with pytest.raises(UnsupportedFeatureError) as excinfo:
        dialect.require("vector", "backs vector search")

    assert "Schema.extension('vector')" in str(excinfo.value)


def test_the_server_version_is_parsed_from_the_drivers_integer():
    from craft.orm.connection import Connection

    connection = Connection({"driver": "pgsql"})

    class _Pdo:
        server_version = 180004

    connection._session().pdo = _Pdo()
    try:
        assert connection.server_version() == (18, 4)
        _Pdo.server_version = 150018
        assert connection.server_version() == (15, 18)
    finally:
        connection._session().pdo = None


def test_a_non_postgres_connection_has_no_server_version():
    from craft.orm.connection import Connection

    assert Connection({"driver": "sqlite", "database": ":memory:"}).server_version() is None


def test_dialect_for_defaults_to_the_narrowest_feature_set():
    assert isinstance(dialect_for("postgresql"), PostgresDialect)
    assert isinstance(dialect_for("mysql"), MySqlDialect)
    assert isinstance(dialect_for("sqlite"), SqliteDialect)
    # An unknown driver must not be optimistically granted Postgres features.
    assert isinstance(dialect_for("cockroach"), SqliteDialect)


def test_the_connection_exposes_its_dialect():
    from craft.orm.connection import Connection

    assert Connection({"driver": "sqlite", "database": ":memory:"}).dialect.name == "sqlite"
    assert Connection({"driver": "pgsql"}).dialect.name == "postgresql"


def test_the_manager_forwards_the_dialect():
    from craft.orm.db import DatabaseManager

    manager = DatabaseManager(config={"driver": "sqlite", "database": ":memory:"})
    assert manager.dialect.name == "sqlite"
    assert manager.dialect.supports("partial_indexes")
