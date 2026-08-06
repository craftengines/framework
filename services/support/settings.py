"""
Global Framework Settings Subsystem.
Category: Subsystem (Core Framework).
Relations:
  - Interacts with Config facade and DB settings table.
References:
  - Skill: `codepy-development` ([SKILL.md](file:///d:/data/www/codepy/.agents/skills/codepy-development/SKILL.md))
"""

from typing import Any, Optional
from codepy.facades import Config, DB


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
                return row[0]
        except Exception:
            pass
        if key in cls._memory_settings:
            return cls._memory_settings[key]
        return Config.get(f"framework.{key}", default)

    @classmethod
    def set(cls, key: str, value: Any) -> None:
        """Set a global setting value in database."""
        val_str = str(value)
        cls._memory_settings[key] = val_str
        try:
            DB.statement(
                "INSERT INTO settings (key, value) VALUES (:key, :val) ON CONFLICT (key) DO UPDATE SET value = :val",
                {"key": key, "val": val_str}
            )
        except Exception:
            try:
                # Fallback for SQLite / generic DB without ON CONFLICT syntax
                DB.statement("DELETE FROM settings WHERE key = :key", {"key": key})
                DB.statement("INSERT INTO settings (key, value) VALUES (:key, :val)", {"key": key, "val": val_str})
            except Exception:
                pass


def setting(key: str, default: Any = None) -> Any:
    """Global helper function to retrieve framework settings."""
    return SettingManager.get(key, default)
