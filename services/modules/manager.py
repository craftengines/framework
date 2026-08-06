"""
ModuleManager — Manages dynamic framework modules discovery and state.
Category: Subsystem (Core Framework).
Relations:
  - Interacts with app.Models.Module.Module model / DB facade for modules table.
References:
  - Skill: `codepy-development` ([SKILL.md](file:///d:/data/www/codepy/.agents/skills/codepy-development/SKILL.md))
"""

from typing import Dict, List, Optional
from codepy.facades import DB


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

    def enable(self, slug: str) -> bool:
        """Enable a module."""
        try:
            DB.statement("UPDATE modules SET enabled = true WHERE slug = :slug", {"slug": slug})
        except Exception:
            pass
        if slug in self._registered_modules:
            self._registered_modules[slug]["enabled"] = True
        return True

    def disable(self, slug: str) -> bool:
        """Disable a module."""
        try:
            DB.statement("UPDATE modules SET enabled = false WHERE slug = :slug", {"slug": slug})
        except Exception:
            pass
        if slug in self._registered_modules:
            self._registered_modules[slug]["enabled"] = False
        return True
