"""Database connection layer for Craft Framework.

Provides a driver-agnostic connection wrapper over sqlite3, psycopg2 (PostgreSQL)
and PyMySQL/mysqlclient (MySQL), normalising placeholders and row access so the
rest of the framework can speak a single dialect-neutral SQL flavour.

Category: Core Framework (ORM).
Relations:
  - Wrapped by `DatabaseManager` (`engine/orm/db.py`), which owns
    read/write splitting and multi-tenant schema switching.
  - No SQLAlchemy or other ORM layer sits underneath this — it talks to the
    driver libraries directly.
References:
  - Guide: `documentation/orm.md`, `documentation/configuration.md#database-connections`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import os
import re
import sqlite3
from typing import Any, Dict, List, Optional, Sequence, Union

Bindings = Union[Sequence[Any], Dict[str, Any], None]

_SCHEMA_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def assert_schema_identifier(name: str) -> str:
    """Reject schema names that could break out of the quoted identifier.

    Postgres schema/search_path values here are built with an f-string, not a
    bound parameter (`SET search_path` cannot take one) — so a tenant name
    such as `a", public; DROP SCHEMA public CASCADE; --` must be rejected
    before it ever reaches the string, not just quoted.
    """
    if not isinstance(name, str) or not _SCHEMA_IDENTIFIER_RE.match(name):
        raise ValueError(f"Invalid schema identifier [{name!r}].")
    return name


class Row:
    """Dict-like row supporting attribute, key and positional access."""

    __slots__ = ("_data",)

    def __init__(self, data: Dict[str, Any]):
        object.__setattr__(self, "_data", dict(data))

    def __getattr__(self, name: str) -> Any:
        data = object.__getattribute__(self, "_data")
        if name in data:
            return data[name]
        raise AttributeError(f"'Row' object has no attribute '{name}'")

    def __getitem__(self, item: Any) -> Any:
        if isinstance(item, str):
            return self._data[item]
        return list(self._data.values())[item]

    def __contains__(self, item: Any) -> bool:
        return item in self._data

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._data)

    def __iter__(self):
        return iter(self._data.items())

    def __len__(self) -> int:
        return len(self._data)

    def __repr__(self) -> str:
        return f"Row({self._data!r})"


class StatementResult:
    """Result of an executed statement."""

    def __init__(self, rows: List[Row], rowcount: int = 0, lastrowid: Any = None):
        self._rows = rows
        self.rowcount = rowcount
        self.lastrowid = lastrowid
        self._cursor_pos = 0

    def fetchall(self) -> List[Row]:
        rows = self._rows[self._cursor_pos:]
        self._cursor_pos = len(self._rows)
        return rows

    def fetchone(self) -> Optional[Row]:
        if self._cursor_pos < len(self._rows):
            row = self._rows[self._cursor_pos]
            self._cursor_pos += 1
            return row
        return None

    def __iter__(self):
        return iter(self._rows)

    def __len__(self) -> int:
        return len(self._rows)


class ConnectionError_(Exception):
    """Raised when a database connection cannot be established."""


# --- placeholder normalisation -------------------------------------------------

_NAMED_RE = re.compile(r"(?<![:\w]):([a-zA-Z_]\w*)")
_STRING_RE = re.compile(r"'(?:[^']|'')*'")


def _protect_strings(sql: str):
    """Replace string literals with tokens so placeholder rewriting skips them."""
    literals: List[str] = []

    def _stash(match: "re.Match[str]") -> str:
        literals.append(match.group(0))
        return f"\x00{len(literals) - 1}\x00"

    return _STRING_RE.sub(_stash, sql), literals


def _restore_strings(sql: str, literals: List[str]) -> str:
    for index, literal in enumerate(literals):
        sql = sql.replace(f"\x00{index}\x00", literal)
    return sql


def normalize_placeholders(sql: str, bindings: Bindings, paramstyle: str):
    """Translate `?` / `:name` placeholders into the driver's paramstyle.

    Returns the rewritten SQL and the bindings shaped for that driver.
    """
    if paramstyle == "qmark":  # sqlite3 understands both forms natively
        return sql, bindings if bindings is not None else []

    protected, literals = _protect_strings(sql)

    if isinstance(bindings, dict):
        if paramstyle == "pyformat":
            protected = _NAMED_RE.sub(lambda m: f"%({m.group(1)})s", protected)
            return _restore_strings(protected, literals), bindings
        # format-style drivers need positional args in appearance order
        order: List[str] = []

        def _to_pos(match: "re.Match[str]") -> str:
            order.append(match.group(1))
            return "%s"

        protected = _NAMED_RE.sub(_to_pos, protected)
        return _restore_strings(protected, literals), [bindings[name] for name in order]

    protected = protected.replace("?", "%s")
    return _restore_strings(protected, literals), list(bindings or [])


class Connection:
    """A single database connection bound to a driver dialect."""

    def __init__(self, config: Dict[str, Any], base_path: Optional[str] = None):
        self.config = dict(config or {})
        self.base_path = base_path or os.getcwd()
        self.driver = (self.config.get("driver") or "sqlite").lower()
        if self.driver in ("pgsql", "postgres"):
            self.driver = "postgresql"
        self.paramstyle = "qmark" if self.driver == "sqlite" else "pyformat"
        self._pdo: Any = None
        self._in_transaction = 0
        self._schema: Optional[str] = None

    # -- lifecycle -------------------------------------------------------------

    @property
    def pdo(self) -> Any:
        if self._pdo is None:
            self._pdo = self._connect()
        return self._pdo

    def _connect(self) -> Any:
        if self.driver == "sqlite":
            return self._connect_sqlite()
        if self.driver == "postgresql":
            return self._connect_postgres()
        if self.driver == "mysql":
            return self._connect_mysql()
        raise ConnectionError_(f"Unsupported database driver [{self.driver}].")

    def _connect_sqlite(self) -> Any:
        database = self.config.get("database") or ":memory:"
        if database not in (":memory:", ""):
            if not os.path.isabs(database):
                database = os.path.join(self.base_path, database)
            directory = os.path.dirname(database)
            if directory:
                os.makedirs(directory, exist_ok=True)
        else:
            database = ":memory:"
        conn = sqlite3.connect(database, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _connect_postgres(self) -> Any:
        try:
            import psycopg2
            import psycopg2.extras
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise ConnectionError_(
                "PostgreSQL driver not installed. Run `pip install psycopg2-binary`."
            ) from exc

        conn = psycopg2.connect(
            host=self.config.get("host", "127.0.0.1"),
            port=int(self.config.get("port", 5432) or 5432),
            dbname=self.config.get("database"),
            user=self.config.get("username"),
            password=self.config.get("password") or None,
            connect_timeout=int(self.config.get("timeout", 10) or 10),
        )
        conn.autocommit = False
        search_path = self.config.get("search_path") or self.config.get("schema")
        if search_path:
            assert_schema_identifier(search_path)
            with conn.cursor() as cursor:
                cursor.execute(f'SET search_path TO "{search_path}", public')
            conn.commit()
        return conn

    def _connect_mysql(self) -> Any:
        try:
            import pymysql
            import pymysql.cursors
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise ConnectionError_(
                "MySQL driver not installed. Run `pip install pymysql`."
            ) from exc

        return pymysql.connect(
            host=self.config.get("host", "127.0.0.1"),
            port=int(self.config.get("port", 3306) or 3306),
            database=self.config.get("database"),
            user=self.config.get("username"),
            password=self.config.get("password") or "",
            charset=self.config.get("charset", "utf8mb4"),
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
        )

    def close(self) -> None:
        if self._pdo is not None:
            try:
                self._pdo.close()
            except Exception:
                pass
            self._pdo = None

    # -- execution -------------------------------------------------------------

    def _cursor(self) -> Any:
        if self.driver == "postgresql":
            import psycopg2.extras

            return self.pdo.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        return self.pdo.cursor()

    def statement(self, sql: str, bindings: Bindings = None) -> StatementResult:
        sql = sql.strip()
        query, params = normalize_placeholders(sql, bindings, self.paramstyle)
        cursor = self._cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            rows = self._fetch(cursor)
            result = StatementResult(rows, cursor.rowcount, self._last_id(cursor))
            if not self._in_transaction:
                self.pdo.commit()
            return result
        except Exception:
            if not self._in_transaction:
                try:
                    self.pdo.rollback()
                except Exception:
                    pass
            raise
        finally:
            try:
                cursor.close()
            except Exception:
                pass

    def _fetch(self, cursor: Any) -> List[Row]:
        if cursor.description is None:
            return []
        try:
            raw = cursor.fetchall()
        except Exception:
            return []
        rows: List[Row] = []
        columns = [d[0] for d in cursor.description]
        for item in raw:
            if isinstance(item, Row):
                rows.append(item)
            elif isinstance(item, dict):
                rows.append(Row(item))
            elif isinstance(item, sqlite3.Row):
                rows.append(Row({key: item[key] for key in item.keys()}))
            else:
                # strict: a row whose arity disagrees with cursor.description is
                # a driver bug — pairing them off silently would drop columns.
                rows.append(Row(dict(zip(columns, item, strict=True))))
        return rows

    def _last_id(self, cursor: Any) -> Any:
        return getattr(cursor, "lastrowid", None)

    # -- transactions ----------------------------------------------------------

    def begin(self) -> None:
        if self._in_transaction == 0 and self.driver == "sqlite":
            # sqlite3 in its default mode never issues BEGIN itself, so without
            # this the "transaction" would not actually be atomic.
            try:
                self.pdo.execute("BEGIN IMMEDIATE")
            except sqlite3.OperationalError:
                pass  # already inside an implicit transaction
        self._in_transaction += 1

    def commit(self) -> None:
        if self._in_transaction:
            self._in_transaction -= 1
        if not self._in_transaction:
            self.pdo.commit()

    def rollback(self) -> None:
        self._in_transaction = 0
        try:
            self.pdo.rollback()
        except Exception:
            pass

    # -- schema helpers --------------------------------------------------------

    def use_schema(self, schema: Optional[str]) -> None:
        """Switch the active PostgreSQL schema (multi-tenancy)."""
        self._schema = schema
        if self.driver != "postgresql" or not schema:
            return
        assert_schema_identifier(schema)
        self.statement(f'SET search_path TO "{schema}", public')

    def table_exists(self, table: str) -> bool:
        if self.driver == "sqlite":
            sql = "SELECT name FROM sqlite_master WHERE type='table' AND name = ?"
        elif self.driver == "postgresql":
            sql = (
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_name = ? AND table_schema = ANY (current_schemas(false))"
            )
        else:
            sql = "SELECT table_name FROM information_schema.tables WHERE table_name = ? AND table_schema = DATABASE()"
        return self.statement(sql, [table]).fetchone() is not None
