"""
Global Framework Settings Subsystem.
Category: Subsystem (Core Framework).
Relations:
  - Interacts with Config facade and DB settings table.
References:
  - Skill: `craft-development` (`.agents/skills/framework/craft-development/SKILL.md`,
    workspace root, outside this repository)
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import json
import logging
from typing import Any, Optional
from craft.facades import Config, DB


def _decode(raw: Any) -> Any:
    """Values are stored JSON-encoded; older rows may hold plain strings."""
    if not isinstance(raw, str):
        return raw
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return raw


class SettingManager:
    """Manages application settings, per tenant when one is bound."""
    _memory_settings = {}

    #: Prefix of a tenant's own row. Namespacing the key keeps the existing
    #: unique `settings.key` constraint doing its job without a table rebuild.
    TENANT_PREFIX = "tenant:"

    @classmethod
    def storage_key(cls, key: str, tenant_id: Optional[str]) -> str:
        """Return the stored key for `key`, namespaced under `tenant_id` when given.

        Args:
            key: The public setting name.
            tenant_id: The owning tenant, or `None` for an installation-wide value.

        Returns:
            The value of the `settings.key` column.
        """
        return f"{cls.TENANT_PREFIX}{tenant_id}:{key}" if tenant_id else key

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """Get a setting: the bound tenant's value, then the installation's, then config.

        A tenant never reads another tenant's row: lookups are keyed by the
        tenant bound in this context, never by the key alone.
        """
        from engine.orm.tenancy import current_tenant_id

        tenant_id = current_tenant_id()
        keys = [cls.storage_key(key, tenant_id), key] if tenant_id else [key]
        for stored_key in keys:
            found, value = cls._lookup(stored_key)
            if found:
                return value
        return Config.get(f"framework.{key}", default)

    @classmethod
    def _lookup(cls, stored_key: str) -> tuple[bool, Any]:
        key = stored_key
        try:
            res = DB.statement("SELECT value FROM settings WHERE key = :key", {"key": key})
            row = res.fetchone()
            if row is not None:
                # By column name: MySQL/PostgreSQL cursors return dicts, where
                # positional indexing raises.
                return True, _decode(row["value"])
        except Exception:
            pass
        if key in cls._memory_settings:
            return True, _decode(cls._memory_settings[key])
        return False, None

    @classmethod
    def set(cls, key: str, value: Any, *, global_scope: bool = False) -> bool:
        """Persist a setting. Returns whether it reached the database.

        With a tenant bound, the value belongs to that tenant unless
        `global_scope=True` writes the installation-wide default.

        It used to return `None` whether the write succeeded or fell through to
        an in-memory dict that dies with the process — so a caller could not
        tell a saved setting from one silently lost at the next restart.
        """
        from engine.orm.tenancy import current_tenant_id

        key = cls.storage_key(key, None if global_scope else current_tenant_id())
        # JSON keeps the type — str(False) round-tripped to the truthy "False".
        val_str = json.dumps(value)
        cls._memory_settings[key] = val_str

        try:
            DB.statement(
                "INSERT INTO settings (key, value) VALUES (:key, :val) ON CONFLICT (key) DO UPDATE SET value = :val",
                {"key": key, "val": val_str}
            )
            return True
        except Exception:
            pass

        try:
            # Fallback for drivers without ON CONFLICT support.
            DB.statement("DELETE FROM settings WHERE key = :key", {"key": key})
            DB.statement("INSERT INTO settings (key, value) VALUES (:key, :val)", {"key": key, "val": val_str})
            return True
        except Exception:
            logging.getLogger("craft").warning(
                "Setting %r could not be persisted and is held in memory only "
                "— it will be lost when this process exits.", key, exc_info=True,
            )
            return False


def setting(key: str, default: Any = None) -> Any:
    """Global helper function to retrieve framework settings."""
    return SettingManager.get(key, default)
