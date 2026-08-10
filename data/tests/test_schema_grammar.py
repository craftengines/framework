"""Schema grammar: the same Blueprint must compile correctly per dialect."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest

from craft.migrations.schema import Blueprint, Grammar


def build(callback) -> Blueprint:
    blueprint = Blueprint("widgets")
    callback(blueprint)
    return blueprint


def compile_for(driver: str, callback) -> str:
    return Grammar(driver).compile_create(build(callback))[0]


class TestColumnTypes:
    def test_auto_increment_key_per_dialect(self):
        sqlite = compile_for("sqlite", lambda t: t.id())
        postgres = compile_for("postgresql", lambda t: t.id())
        mysql = compile_for("mysql", lambda t: t.id())

        assert "INTEGER PRIMARY KEY AUTOINCREMENT" in sqlite
        assert "BIGSERIAL PRIMARY KEY" in postgres
        assert "AUTO_INCREMENT PRIMARY KEY" in mysql

    def test_id_type_integer_narrows_the_key(self):
        assert "SERIAL PRIMARY KEY" in compile_for(
            "postgresql", lambda t: t.id(type="integer")
        )

    def test_json_maps_to_jsonb_only_on_postgres(self):
        assert "JSONB" in compile_for("postgresql", lambda t: t.json("meta"))
        assert "TEXT" in compile_for("sqlite", lambda t: t.json("meta"))
        assert "JSON" in compile_for("mysql", lambda t: t.json("meta"))

    def test_boolean_default_uses_native_literal(self):
        postgres = compile_for("postgresql", lambda t: t.boolean("active").default(True))
        sqlite = compile_for("sqlite", lambda t: t.boolean("active").default(True))

        assert "DEFAULT TRUE" in postgres
        assert "DEFAULT 1" in sqlite

    def test_string_length_is_honoured(self):
        assert "VARCHAR(100)" in compile_for("sqlite", lambda t: t.string("token", 100))

    def test_decimal_precision_and_scale(self):
        sql = compile_for("postgresql", lambda t: t.decimal("amount", 10, 4))
        assert "NUMERIC(10, 4)" in sql

    def test_uuid_falls_back_to_varchar_off_postgres(self):
        assert "UUID" in compile_for("postgresql", lambda t: t.uuid("ref"))
        assert "VARCHAR(36)" in compile_for("sqlite", lambda t: t.uuid("ref"))


class TestModifiers:
    def test_fluent_and_keyword_styles_are_equivalent(self):
        fluent = compile_for("sqlite", lambda t: t.string("cpf").nullable())
        keyword = compile_for("sqlite", lambda t: t.string("cpf", nullable=True))
        assert fluent == keyword

    def test_not_null_is_the_default(self):
        assert "NOT NULL" in compile_for("sqlite", lambda t: t.string("name"))

    def test_nullable_drops_not_null(self):
        assert "NOT NULL" not in compile_for("sqlite", lambda t: t.string("name").nullable())

    def test_unique_is_emitted(self):
        assert "UNIQUE" in compile_for("sqlite", lambda t: t.string("email").unique())

    def test_string_default_is_quoted_and_escaped(self):
        sql = compile_for("sqlite", lambda t: t.string("note").default("O'Brien"))
        assert "DEFAULT 'O''Brien'" in sql

    def test_timestamps_adds_both_columns_as_nullable(self):
        blueprint = build(lambda t: t.timestamps())
        names = [c.name for c in blueprint.columns]
        assert names == ["created_at", "updated_at"]
        assert all(c.is_nullable for c in blueprint.columns)


class TestConstraintsAndIndexes:
    def test_constrained_infers_the_related_table(self):
        sql = compile_for("sqlite", lambda t: t.foreign_id("user_id").constrained())
        assert 'FOREIGN KEY ("user_id") REFERENCES "users" ("id")' in sql

    def test_cascade_on_delete(self):
        sql = compile_for(
            "sqlite", lambda t: t.foreign_id("post_id").constrained().cascade_on_delete()
        )
        assert "ON DELETE CASCADE" in sql

    def test_composite_unique_index_is_a_separate_statement(self):
        blueprint = build(lambda t: (t.id(), t.unique_index(["tenant_id", "slug"])))
        statements = Grammar("postgresql").compile_create(blueprint)
        assert len(statements) == 2
        assert "CREATE UNIQUE INDEX" in statements[1]


class TestDropAndAlter:
    def test_drop_cascades_only_on_postgres(self):
        assert Grammar("postgresql").compile_drop("widgets").endswith("CASCADE")
        assert not Grammar("sqlite").compile_drop("widgets").endswith("CASCADE")

    def test_add_columns_emits_one_alter_per_column(self):
        blueprint = build(lambda t: (t.string("a"), t.string("b")))
        statements = Grammar("sqlite").compile_add_columns(blueprint)
        assert len(statements) == 2
        assert all(s.startswith("ALTER TABLE") for s in statements)

    def test_identifier_quoting_per_dialect(self):
        assert Grammar("mysql").wrap("order") == "`order`"
        assert Grammar("postgresql").wrap("order") == '"order"'
