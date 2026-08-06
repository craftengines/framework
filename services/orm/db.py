"""Database Manager for Codepy Framework ORM.

Config-driven, multi-driver (SQLite / PostgreSQL / MySQL) connection manager with
read-write splitting, transactions and PostgreSQL schema-based multi-tenancy.
"""

from __future__ import annotations

import os
from typing import Any, Callable, Dict, List, Optional

from services.orm.connection import (
    Bindings,
    Connection,
    Row,
    StatementResult,
)

# Backwards-compatible aliases (previous sqlite-only API).
RowWrapper = Row
DatabaseStatementResult = StatementResult


class DatabaseManager:
    """Resolves and manages database connections from the application config."""

    def __init__(self, app: Optional[Any] = None, config: Optional[Dict[str, Any]] = None):
        self.app = app
        self.base_path = getattr(app, "base_path", None) or os.getcwd()
        self._connections: Dict[str, Connection] = {}
        self._default: Optional[str] = None
        self._write: Optional[Connection] = None
        self._read: Optional[Connection] = None
        self._explicit_config = config
        self._tenant_schema: Optional[str] = None
        self._booted = False

    # -- configuration ---------------------------------------------------------

    def _config(self) -> Any:
        if self.app is not None:
            try:
                return self.app.make("config")
            except Exception:
                return None
        return None

    def _resolve_config(self, name: Optional[str] = None) -> Dict[str, Any]:
        if self._explicit_config is not None:
            return self._explicit_config

        config = self._config()
        if config is None:
            return {"driver": "sqlite", "database": ":memory:"}

        name = name or config.get("database.default") or "sqlite"
        self._default = name
        resolved = config.get(f"database.connections.{name}")
        if not isinstance(resolved, dict):
            return {"driver": "sqlite", "database": ":memory:"}
        return resolved

    def boot(self, name: Optional[str] = None) -> "DatabaseManager":
        """(Re)build the read/write connections from the current config."""
        conn_config = dict(self._resolve_config(name))

        write_config = dict(conn_config)
        write_config.pop("read", None)
        write_config.pop("write", None)
        if isinstance(conn_config.get("write"), dict):
            write_config.update(conn_config["write"])

        self._write = Connection(write_config, self.base_path)

        if isinstance(conn_config.get("read"), dict):
            read_config = dict(conn_config)
            read_config.pop("read", None)
            read_config.pop("write", None)
            read_config.update(conn_config["read"])
            self._read = Connection(read_config, self.base_path)
        else:
            self._read = None

        self._booted = True
        if self._tenant_schema:
            self.set_tenant_schema(self._tenant_schema)
        return self

    # -- connections -----------------------------------------------------------

    @property
    def write_connection(self) -> Connection:
        if self._write is None:
            self.boot()
        assert self._write is not None
        return self._write

    @property
    def read_connection(self) -> Connection:
        if not self._booted:
            self.boot()
        return self._read or self.write_connection

    @property
    def driver(self) -> str:
        return self.write_connection.driver

    def connection(self, name: Optional[str] = None) -> Connection:
        """Get (and cache) a named connection from the config."""
        if name is None:
            return self.write_connection
        if name not in self._connections:
            self._connections[name] = Connection(self._resolve_config(name), self.base_path)
        return self._connections[name]

    def purge(self) -> None:
        """Close every open connection."""
        for connection in list(self._connections.values()):
            connection.close()
        self._connections.clear()
        if self._write is not None:
            self._write.close()
        if self._read is not None:
            self._read.close()
        self._write = self._read = None
        self._booted = False

    # -- statements ------------------------------------------------------------

    def statement(self, query: str, bindings: Bindings = None, read: bool = False) -> StatementResult:
        connection = self.read_connection if read else self.write_connection
        return connection.statement(query, bindings)

    def select(self, query: str, bindings: Bindings = None) -> List[Row]:
        return self.statement(query, bindings, read=True).fetchall()

    def select_one(self, query: str, bindings: Bindings = None) -> Optional[Row]:
        return self.statement(query, bindings, read=True).fetchone()

    def insert(self, query: str, bindings: Bindings = None) -> StatementResult:
        return self.statement(query, bindings)

    def update(self, query: str, bindings: Bindings = None) -> int:
        return self.statement(query, bindings).rowcount

    def delete(self, query: str, bindings: Bindings = None) -> int:
        return self.statement(query, bindings).rowcount

    def insert_get_id(self, table: str, values: Dict[str, Any], key: str = "id") -> Any:
        """Insert a row and return its primary key across all supported drivers."""
        columns = list(values.keys())
        column_sql = ", ".join(f'"{c}"' if self.driver != "mysql" else f"`{c}`" for c in columns)
        placeholders = ", ".join(["?"] * len(columns))
        params = [values[c] for c in columns]
        table_sql = f'"{table}"' if self.driver != "mysql" else f"`{table}`"

        if self.driver == "postgresql":
            result = self.statement(
                f"INSERT INTO {table_sql} ({column_sql}) VALUES ({placeholders}) RETURNING {key}",
                params,
            )
            row = result.fetchone()
            return row[key] if row is not None else None

        result = self.statement(
            f"INSERT INTO {table_sql} ({column_sql}) VALUES ({placeholders})", params
        )
        if result.lastrowid:
            return result.lastrowid
        if key in values:
            return values[key]
        return None

    def table(self, table_name: str) -> Any:
        from services.orm.query_builder import QueryBuilder

        return QueryBuilder(table_name=table_name, db=self)

    def table_exists(self, table: str) -> bool:
        return self.write_connection.table_exists(table)

    # -- transactions ----------------------------------------------------------

    def transaction(self, callback: Callable[[], Any]) -> Any:
        connection = self.write_connection
        connection.begin()
        try:
            result = callback()
            connection.commit()
            return result
        except Exception:
            connection.rollback()
            raise

    def begin_transaction(self) -> None:
        self.write_connection.begin()

    def commit(self) -> None:
        self.write_connection.commit()

    def rollback(self) -> None:
        self.write_connection.rollback()

    # -- multi-tenancy ---------------------------------------------------------

    def set_tenant_schema(self, schema_name: Optional[str] = None) -> None:
        """Point the connection at a tenant schema (PostgreSQL `search_path`)."""
        self._tenant_schema = schema_name
        if self.driver != "postgresql":
            return
        self.write_connection.use_schema(schema_name)
        if self._read is not None:
            self._read.use_schema(schema_name)

    def create_tenant_schema(self, schema_name: str) -> None:
        if self.driver != "postgresql":
            raise RuntimeError("Tenant schemas require the PostgreSQL driver.")
        self.statement(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"')

    def ensure_tenant_schema(self, schema_name: str, owner: Any = None) -> bool:
        """Create the tenant schema and migrate it if it is new.

        Returns True when the schema was provisioned by this call. A no-op on
        drivers without schema support, so tenant-aware middleware can run
        unchanged against SQLite in development and tests.
        """
        if self.driver != "postgresql" or not schema_name:
            return False

        existing = self.statement(
            "SELECT schema_name FROM information_schema.schemata WHERE schema_name = ?",
            [schema_name],
            read=True,
        ).fetchone()
        if existing is not None:
            self.set_tenant_schema(schema_name)
            return False

        self.create_tenant_schema(schema_name)
        self.set_tenant_schema(schema_name)

        if self.app is not None:
            from services.migrations.migrator import Migrator

            Migrator(self.app).run()
        return True

    # -- test / swap helpers ---------------------------------------------------

    def _swap(self, db_mgr: "DatabaseManager") -> None:
        self._write = db_mgr.write_connection
        self._read = db_mgr._read
        self._booted = True

    def _clear_resolved(self) -> None:
        self._connections.clear()
