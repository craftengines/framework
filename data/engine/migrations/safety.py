"""Refusal of schema-wide destructive operations on permanent databases.

NR-02 bans wiping a database in every environment. A database counts as
disposable only when it is in-memory SQLite, its name ends in `_test`, or it is
listed in `database.disposable_databases` (`DB_DISPOSABLE_DATABASES`). Anything
else is permanent by default, and production is always permanent.

Category: Core Framework (Migrations).
Relations:
  - Called by `engine/migrations/migrator.py` before `drop_all_tables`, `reset`
    and `refresh`, which back `dev.py migrate fresh|reset|refresh` and
    `dev.py db wipe`.
References:
  - Standard: `.claude/rules/RELEASE_NON_REGRESSION_STANDARD.md` (NR-02)
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import os
from collections.abc import Iterable
from typing import Any

DISPOSABLE_SUFFIX = "_test"
IN_MEMORY_DATABASES = frozenset({"", ":memory:"})


class DestructiveOperationRefused(RuntimeError):
    """Raised when a schema-wide destructive operation targets a permanent database."""

    code = "DATABASE_DESTRUCTIVE_OPERATION_REFUSED"
    message_key = "database.safety.destructive_operation_refused"

    def __init__(self, operation: str, database: str, environment: str, reason: str | None = None) -> None:
        """Build the refusal.

        Args:
            operation: The refused operation, e.g. `drop_all_tables`.
            database: The target database name.
            environment: The application environment at refusal time.
            reason: Optional context beyond the environment, e.g. "the query
                builder is scoped to a tenant" for a refusal that has nothing
                to do with which environment is running.
        """
        detail = reason if reason is not None else environment
        super().__init__(f"{self.code}: {operation} on '{database}' ({detail})")
        self.params = {"operation": operation, "database": database, "environment": environment, "reason": reason}


def is_disposable_database(driver: str, database: str, allowlist: Iterable[str] = ()) -> bool:
    """Return whether a database may be wiped.

    Args:
        driver: Normalized driver name (`sqlite`, `postgresql`, `mysql`).
        database: The configured database name or SQLite path.
        allowlist: Extra database names declared disposable.

    Returns:
        `True` only for in-memory SQLite, a `_test` suffix, or an allowlisted name.
    """
    name = str(database or "").strip()
    if driver == "sqlite" and name in IN_MEMORY_DATABASES:
        return True
    stem = os.path.splitext(os.path.basename(name))[0] if driver == "sqlite" else name
    return stem.endswith(DISPOSABLE_SUFFIX) or name in {item.strip() for item in allowlist if item.strip()}


def _config_value(app: Any, key: str, default: Any) -> Any:
    try:
        return app.make("config").get(key, default)
    except (AttributeError, KeyError):
        return default


def assert_disposable(app: Any, db: Any, operation: str) -> None:
    """Raise unless the database behind `db` is disposable outside production.

    Args:
        app: The application container, used to read configuration.
        db: The database manager whose write connection is the target.
        operation: Name of the operation being attempted.

    Raises:
        DestructiveOperationRefused: When the target database is permanent.
    """
    environment = str(_config_value(app, "app.APP_ENV", os.environ.get("APP_ENV", "local")))
    raw = _config_value(app, "database.disposable_databases", os.environ.get("DB_DISPOSABLE_DATABASES", ""))
    allowlist = raw.split(",") if isinstance(raw, str) else list(raw or ())
    driver = str(getattr(db, "driver", "sqlite"))
    database = str(db.write_connection.config.get("database") or "")
    if environment == "production" or not is_disposable_database(driver, database, allowlist):
        raise DestructiveOperationRefused(operation, database, environment)
