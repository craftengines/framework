"""Schema builder for Craft Framework migrations.

Provides a fluent `Blueprint` that compiles to dialect-specific
DDL for SQLite, PostgreSQL and MySQL.

Category: Core Framework (Migrations).
Relations:
  - Used inside `database/migrations/*` files' `up()`/`down()`; executes DDL
    through `services/orm/connection.py`. Bound as `schema`, exposed via the
    `Schema` facade.
References:
  - Guide: `documentation/migrations.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from typing import Any, Callable, List, Optional


def _plural(word: str) -> str:
    if word.endswith("y") and not word.endswith(("ay", "ey", "iy", "oy", "uy")):
        return word[:-1] + "ies"
    if word.endswith(("s", "x", "z", "ch", "sh")):
        return word + "es"
    return word + "s"


class _NoDefault:
    def __repr__(self) -> str:
        return "<no default>"


_NO_DEFAULT = _NoDefault()


class Column:
    """A fluent column definition."""

    def __init__(self, name: str, type_: str, length: Optional[Any] = None):
        self.name = name
        self.type = type_
        self.length = length
        self.is_nullable = False
        self.is_unique = False
        self.is_primary = False
        self.is_auto_increment = False
        self.default_value: Any = _NO_DEFAULT
        self.foreign: Optional[dict] = None
        self.index = False
        self.comment: Optional[str] = None

    # -- fluent modifiers ------------------------------------------------------

    def nullable(self, value: bool = True) -> "Column":
        self.is_nullable = value
        return self

    def unique(self, value: bool = True) -> "Column":
        self.is_unique = value
        return self

    def default(self, value: Any) -> "Column":
        self.default_value = value
        return self

    def primary(self) -> "Column":
        self.is_primary = True
        return self

    def indexed(self) -> "Column":
        self.index = True
        return self

    def constrained(self, table: Optional[str] = None, column: str = "id") -> "Column":
        target = table or _plural(self.name[:-3] if self.name.endswith("_id") else self.name)
        self.foreign = {"table": target, "column": column, "on_delete": None, "on_update": None}
        return self

    def references(self, column: str) -> "Column":
        self.foreign = self.foreign or {"table": None, "column": column, "on_delete": None, "on_update": None}
        self.foreign["column"] = column
        return self

    def on(self, table: str) -> "Column":
        self.foreign = self.foreign or {"table": table, "column": "id", "on_delete": None, "on_update": None}
        self.foreign["table"] = table
        return self

    def cascade_on_delete(self) -> "Column":
        if self.foreign is None:
            self.constrained()
        self.foreign["on_delete"] = "CASCADE"
        return self

    def null_on_delete(self) -> "Column":
        if self.foreign is None:
            self.constrained()
        self.foreign["on_delete"] = "SET NULL"
        self.is_nullable = True
        return self

    def cascade_on_update(self) -> "Column":
        if self.foreign is None:
            self.constrained()
        self.foreign["on_update"] = "CASCADE"
        return self


class Blueprint:
    """Collects column definitions for a table."""

    def __init__(self, table: str):
        self.table = table
        self.columns: List[Column] = []
        self.indexes: List[dict] = []

    def _add(self, column: Column, **modifiers: Any) -> Column:
        """Append a column, applying any keyword-style modifiers.

        Both styles are supported and interchangeable:
            t.string("cpf").nullable()
            t.string("cpf", nullable=True)
        """
        if modifiers.get("nullable"):
            column.nullable()
        if modifiers.get("unique"):
            column.unique()
        if modifiers.get("index"):
            column.indexed()
        if modifiers.get("primary"):
            column.primary()
        if "default" in modifiers:
            column.default(modifiers["default"])
        self.columns.append(column)
        return column

    # -- column types ----------------------------------------------------------

    def id(self, name: str = "id", type: str = "big", **modifiers: Any) -> Column:
        kind = "increments" if str(type).lower() in ("int", "integer") else "big_increments"
        col = Column(name, kind)
        col.is_primary = True
        col.is_auto_increment = True
        return self._add(col, **modifiers)

    def big_increments(self, name: str = "id", **modifiers: Any) -> Column:
        col = Column(name, "big_increments")
        col.is_primary = True
        col.is_auto_increment = True
        return self._add(col, **modifiers)

    def increments(self, name: str = "id", **modifiers: Any) -> Column:
        col = Column(name, "increments")
        col.is_primary = True
        col.is_auto_increment = True
        return self._add(col, **modifiers)

    def string(self, name: str, length: int = 255, **modifiers: Any) -> Column:
        return self._add(Column(name, "string", length), **modifiers)

    def char(self, name: str, length: int = 255, **modifiers: Any) -> Column:
        return self._add(Column(name, "char", length), **modifiers)

    def text(self, name: str, **modifiers: Any) -> Column:
        return self._add(Column(name, "text"), **modifiers)

    def long_text(self, name: str, **modifiers: Any) -> Column:
        return self._add(Column(name, "long_text"), **modifiers)

    def integer(self, name: str, **modifiers: Any) -> Column:
        return self._add(Column(name, "integer"), **modifiers)

    def big_integer(self, name: str, **modifiers: Any) -> Column:
        return self._add(Column(name, "big_integer"), **modifiers)

    def small_integer(self, name: str, **modifiers: Any) -> Column:
        return self._add(Column(name, "small_integer"), **modifiers)

    def float(self, name: str, **modifiers: Any) -> Column:
        return self._add(Column(name, "float"), **modifiers)

    def decimal(self, name: str, precision: int = 12, scale: int = 2, **modifiers: Any) -> Column:
        return self._add(Column(name, "decimal", (precision, scale)), **modifiers)

    def boolean(self, name: str, **modifiers: Any) -> Column:
        return self._add(Column(name, "boolean"), **modifiers)

    def date(self, name: str, **modifiers: Any) -> Column:
        return self._add(Column(name, "date"), **modifiers)

    def datetime(self, name: str, **modifiers: Any) -> Column:
        return self._add(Column(name, "datetime"), **modifiers)

    def timestamp(self, name: str, **modifiers: Any) -> Column:
        return self._add(Column(name, "datetime"), **modifiers)

    def time(self, name: str, **modifiers: Any) -> Column:
        return self._add(Column(name, "time"), **modifiers)

    def json(self, name: str, **modifiers: Any) -> Column:
        return self._add(Column(name, "json"), **modifiers)

    def uuid(self, name: str = "uuid", **modifiers: Any) -> Column:
        return self._add(Column(name, "uuid"), **modifiers)

    def uuid_key(self, name: str = "uuid") -> Column:
        """A unique, indexed UUID alongside the numeric primary key.

        The integer `id` stays the key for joins and foreign keys — narrow and
        fast — while the UUID is what you expose in URLs and APIs. Sequential
        ids in a public URL leak how many records exist and invite enumeration.

        Models fill this in automatically; see `Model.uses_uuid`.
        """
        return self._add(Column(name, "uuid").unique())

    def uuid_primary(self, name: str = "id") -> Column:
        """Use a UUID as the primary key itself, with no integer id.

        Set `key_type = "uuid"` on the model so it generates the value.
        """
        return self._add(Column(name, "uuid").primary())

    def binary(self, name: str, **modifiers: Any) -> Column:
        return self._add(Column(name, "binary"), **modifiers)

    def enum(self, name: str, values: List[str], **modifiers: Any) -> Column:
        col = Column(name, "string", 255)
        col.comment = "enum:" + ",".join(values)
        return self._add(col, **modifiers)

    def foreign_id(self, name: str, **modifiers: Any) -> Column:
        return self._add(Column(name, "big_integer"), **modifiers)

    def timestamps(self) -> None:
        self._add(Column("created_at", "datetime").nullable())
        self._add(Column("updated_at", "datetime").nullable())

    def soft_deletes(self, name: str = "deleted_at") -> Column:
        return self._add(Column(name, "datetime").nullable())

    def remember_token(self) -> Column:
        return self._add(Column("remember_token", "string", 100).nullable())

    def unique_index(self, columns: List[str], name: Optional[str] = None) -> None:
        self.indexes.append({"columns": columns, "unique": True, "name": name})

    def index_on(self, columns: List[str], name: Optional[str] = None) -> None:
        self.indexes.append({"columns": columns, "unique": False, "name": name})


class Grammar:
    """Compiles a Blueprint into dialect-specific SQL."""

    TYPES = {
        "sqlite": {
            "increments": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "big_increments": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "string": "VARCHAR({length})",
            "char": "CHAR({length})",
            "text": "TEXT",
            "long_text": "TEXT",
            "integer": "INTEGER",
            "big_integer": "INTEGER",
            "small_integer": "INTEGER",
            "float": "REAL",
            "decimal": "NUMERIC({precision}, {scale})",
            "boolean": "BOOLEAN",
            "date": "DATE",
            "datetime": "DATETIME",
            "time": "TIME",
            "json": "TEXT",
            "uuid": "VARCHAR(36)",
            "binary": "BLOB",
        },
        "postgresql": {
            "increments": "SERIAL PRIMARY KEY",
            "big_increments": "BIGSERIAL PRIMARY KEY",
            "string": "VARCHAR({length})",
            "char": "CHAR({length})",
            "text": "TEXT",
            "long_text": "TEXT",
            "integer": "INTEGER",
            "big_integer": "BIGINT",
            "small_integer": "SMALLINT",
            "float": "DOUBLE PRECISION",
            "decimal": "NUMERIC({precision}, {scale})",
            "boolean": "BOOLEAN",
            "date": "DATE",
            "datetime": "TIMESTAMP",
            "time": "TIME",
            "json": "JSONB",
            "uuid": "UUID",
            "binary": "BYTEA",
        },
        "mysql": {
            "increments": "INT UNSIGNED AUTO_INCREMENT PRIMARY KEY",
            "big_increments": "BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY",
            "string": "VARCHAR({length})",
            "char": "CHAR({length})",
            "text": "TEXT",
            "long_text": "LONGTEXT",
            "integer": "INT",
            "big_integer": "BIGINT",
            "small_integer": "SMALLINT",
            "float": "DOUBLE",
            "decimal": "DECIMAL({precision}, {scale})",
            "boolean": "TINYINT(1)",
            "date": "DATE",
            "datetime": "DATETIME",
            "time": "TIME",
            "json": "JSON",
            "uuid": "CHAR(36)",
            "binary": "BLOB",
        },
    }

    def __init__(self, driver: str = "sqlite"):
        self.driver = driver if driver in self.TYPES else "sqlite"

    def wrap(self, identifier: str) -> str:
        if self.driver == "mysql":
            return f"`{identifier}`"
        return f'"{identifier}"'

    def type_of(self, column: Column) -> str:
        template = self.TYPES[self.driver][column.type]
        if column.type == "decimal":
            precision, scale = column.length or (12, 2)
            return template.format(precision=precision, scale=scale)
        if "{length}" in template:
            return template.format(length=column.length or 255)
        return template

    def format_default(self, value: Any) -> str:
        if value is None:
            return "NULL"
        if isinstance(value, bool):
            if self.driver == "postgresql":
                return "TRUE" if value else "FALSE"
            return "1" if value else "0"
        if isinstance(value, (int, float)):
            return str(value)
        escaped = str(value).replace("'", "''")
        return f"'{escaped}'"

    def compile_column(self, column: Column) -> str:
        parts = [self.wrap(column.name), self.type_of(column)]

        if column.is_auto_increment:
            return " ".join(parts)

        if not column.is_nullable:
            parts.append("NOT NULL")
        if column.default_value is not _NO_DEFAULT:
            parts.append(f"DEFAULT {self.format_default(column.default_value)}")
        if column.is_primary:
            parts.append("PRIMARY KEY")
        if column.is_unique:
            parts.append("UNIQUE")
        return " ".join(parts)

    def compile_create(self, blueprint: Blueprint) -> List[str]:
        definitions = [self.compile_column(c) for c in blueprint.columns]

        for column in blueprint.columns:
            if column.foreign and column.foreign.get("table"):
                clause = (
                    f"FOREIGN KEY ({self.wrap(column.name)}) REFERENCES "
                    f"{self.wrap(column.foreign['table'])} ({self.wrap(column.foreign['column'])})"
                )
                if column.foreign.get("on_delete"):
                    clause += f" ON DELETE {column.foreign['on_delete']}"
                if column.foreign.get("on_update"):
                    clause += f" ON UPDATE {column.foreign['on_update']}"
                definitions.append(clause)

        body = ",\n    ".join(definitions)
        statements = [
            f"CREATE TABLE IF NOT EXISTS {self.wrap(blueprint.table)} (\n    {body}\n)"
        ]

        for column in blueprint.columns:
            if column.index and not column.is_unique:
                name = f"idx_{blueprint.table}_{column.name}"
                statements.append(
                    f"CREATE INDEX IF NOT EXISTS {self.wrap(name)} "
                    f"ON {self.wrap(blueprint.table)} ({self.wrap(column.name)})"
                )

        for index in blueprint.indexes:
            name = index["name"] or (
                ("uniq_" if index["unique"] else "idx_")
                + blueprint.table
                + "_"
                + "_".join(index["columns"])
            )
            unique = "UNIQUE " if index["unique"] else ""
            cols = ", ".join(self.wrap(c) for c in index["columns"])
            statements.append(
                f"CREATE {unique}INDEX IF NOT EXISTS {self.wrap(name)} "
                f"ON {self.wrap(blueprint.table)} ({cols})"
            )

        return statements

    def compile_drop(self, table: str) -> str:
        cascade = " CASCADE" if self.driver == "postgresql" else ""
        return f"DROP TABLE IF EXISTS {self.wrap(table)}{cascade}"

    def compile_add_columns(self, blueprint: Blueprint) -> List[str]:
        return [
            f"ALTER TABLE {self.wrap(blueprint.table)} ADD COLUMN {self.compile_column(c)}"
            for c in blueprint.columns
        ]

    def compile_drop_column(self, table: str, column: str) -> str:
        return f"ALTER TABLE {self.wrap(table)} DROP COLUMN {self.wrap(column)}"

    def compile_rename(self, table: str, new_name: str) -> str:
        return f"ALTER TABLE {self.wrap(table)} RENAME TO {self.wrap(new_name)}"


class SchemaBuilder:
    """Runs schema operations against the resolved database connection."""

    def __init__(self, db: Any = None):
        self._db = db

    @property
    def db(self) -> Any:
        if self._db is not None:
            return self._db
        from services.container.application import Container

        return Container.getInstance().make("db")

    def grammar(self) -> Grammar:
        return Grammar(getattr(self.db, "driver", "sqlite"))

    def create_table(self, table: str, callback: Callable[[Blueprint], Any]) -> None:
        blueprint = Blueprint(table)
        callback(blueprint)
        for statement in self.grammar().compile_create(blueprint):
            self.db.statement(statement)

    def create(self, table: str, callback: Callable[[Blueprint], Any]) -> None:
        """Alias of :meth:`create_table`."""
        self.create_table(table, callback)

    def table(self, table: str, callback: Callable[[Blueprint], Any]) -> None:
        """Add columns to an existing table."""
        blueprint = Blueprint(table)
        callback(blueprint)
        for statement in self.grammar().compile_add_columns(blueprint):
            self.db.statement(statement)

    def drop_table(self, table: str) -> None:
        self.db.statement(self.grammar().compile_drop(table))

    def drop_if_exists(self, table: str) -> None:
        self.drop_table(table)

    def drop(self, table: str) -> None:
        self.drop_table(table)

    def drop_column(self, table: str, column: str) -> None:
        self.db.statement(self.grammar().compile_drop_column(table, column))

    def rename(self, table: str, new_name: str) -> None:
        self.db.statement(self.grammar().compile_rename(table, new_name))

    def has_table(self, table: str) -> bool:
        return self.db.table_exists(table)

    def has_column(self, table: str, column: str) -> bool:
        return column in self.column_listing(table)

    def column_listing(self, table: str) -> List[str]:
        driver = getattr(self.db, "driver", "sqlite")
        if driver == "sqlite":
            rows = self.db.statement(f'PRAGMA table_info("{table}")').fetchall()
            return [row["name"] for row in rows]
        if driver == "postgresql":
            sql = (
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = ? AND table_schema = ANY (current_schemas(false))"
            )
        else:
            sql = (
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = ? AND table_schema = DATABASE()"
            )
        rows = self.db.statement(sql, [table]).fetchall()
        return [row["column_name"] for row in rows]


# Module-level facade used by migration files: `from craft.migrations import Schema`
Schema = SchemaBuilder()
