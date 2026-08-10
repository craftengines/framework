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
    """Manages global application and framework settings."""
    _memory_settings = {}

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """Get a global setting value from database or config."""
        try:
            res = DB.statement("SELECT value FROM settings WHERE key = :key", {"key": key})
            row = res.fetchone()
            if row is not None:
                # By column name: MySQL/PostgreSQL cursors return dicts, where
                # positional indexing raises.
                return _decode(row["value"])
        except Exception:
            pass
        if key in cls._memory_settings:
            return _decode(cls._memory_settings[key])
        return Config.get(f"framework.{key}", default)

    @classmethod
    def set(cls, key: str, value: Any) -> bool:
        """Persist a global setting. Returns whether it reached the database.

        It used to return `None` whether the write succeeded or fell through to
        an in-memory dict that dies with the process — so a caller could not
        tell a saved setting from one silently lost at the next restart.
        """
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
