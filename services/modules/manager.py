"""
ModuleManager — Manages dynamic framework modules discovery and state.
Category: Subsystem (Core Framework).
Relations:
  - Interacts with app.Models.Module.Module model / DB facade for modules table.
References:
  - Skill: `craft-development` ([SKILL.md](file:///d:/data/www/craft/.agents/skills/craft-development/SKILL.md))
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from typing import Dict, List, Optional
from craft.facades import DB


class ModuleManager:
    """Manages application modules state and lifecycle."""

    def __init__(self):
        self._registered_modules: Dict[str, dict] = {}

    def register(self, slug: str, name: str, description: str = "", version: str = "1.0.0") -> None:
        """Register a module in memory."""
        self._registered_modules[slug] = {
            "slug": slug,
            "name": name,
            "description": description,
            "version": version,
            "enabled": True,
        }

    def all(self) -> List[dict]:
        """Fetch all modules registered in DB or memory."""
        try:
            res = DB.statement("SELECT slug, name, enabled FROM modules")
            rows = res.fetchall()
            if rows:
                return [{"slug": r[0], "name": r[1], "enabled": bool(r[2])} for r in rows]
        except Exception:
            pass
        return list(self._registered_modules.values())

    def is_enabled(self, slug: str) -> bool:
        """Check if a module is enabled."""
        try:
            res = DB.statement("SELECT enabled FROM modules WHERE slug = :slug", {"slug": slug})
            row = res.fetchone()
            if row is not None:
                return bool(row[0])
        except Exception:
            pass
        mod = self._registered_modules.get(slug)
        return mod["enabled"] if mod else False

    def _set_enabled(self, slug: str, enabled: bool) -> bool:
        """Flip a module's state. Returns whether the module was found."""
        affected = 0
        try:
            result = DB.statement(
                "UPDATE modules SET enabled = :enabled WHERE slug = :slug",
                {"enabled": enabled, "slug": slug},
            )
            affected = getattr(result, "rowcount", 0) or 0
        except Exception:
            affected = 0

        in_memory = slug in self._registered_modules
        if in_memory:
            self._registered_modules[slug]["enabled"] = enabled

        # Report what actually happened. Returning True unconditionally — as
        # this used to — made "enable a module that does not exist" look like a
        # success.
        return affected > 0 or in_memory

    def enable(self, slug: str) -> bool:
        """Enable a module. Returns False when there is no such module."""
        return self._set_enabled(slug, True)

    def disable(self, slug: str) -> bool:
        """Disable a module. Returns False when there is no such module."""
        return self._set_enabled(slug, False)
