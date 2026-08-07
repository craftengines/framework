"""
PluginManager — Third-party plugins discovery and lifecycle management.
Category: Subsystem (Core Framework).
Relations:
  - Registers, boots, and triggers hooks across third-party framework plugins.
  - Discovers plugins on disk under `<base_path>/plugins/<slug>/plugin.py` and
    persists their state via the `plugins` table / DB facade, following the
    same DB-first-with-in-memory-fallback pattern as `services.modules.manager`.
References:
  - Skill: `craft-development` (`.agents/skills/framework/craft-development/SKILL.md`,
    workspace root, outside this repository)
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import importlib.util
import os
from typing import Callable, Dict, List, Any

from craft.facades import DB


class PluginManager:
    """Manages external framework plugins, hooks, and extensions."""

    def __init__(self):
        self._plugins: Dict[str, dict] = {}
        self._hooks: Dict[str, List[Callable]] = {}
        # Disk-discovered plugin state, keyed by slug — separate from
        # `_plugins`, which holds the in-memory hook-style registrations made
        # via `register()`/`activate()`/`deactivate()`.
        self._registered_slugs: Dict[str, dict] = {}

    def register(self, name: str, plugin_class_or_dict: Any) -> None:
        """Register a new plugin."""
        self._plugins[name] = {
            "name": name,
            "instance": plugin_class_or_dict,
            "active": True
        }

    def all(self) -> List[dict]:
        """List every in-memory hook-style plugin registration.

        This is distinct from `installed()`, which lists disk-discovered,
        DB-persisted plugins (slug/name/enabled/path) — the two registries
        track different things and are not interchangeable.
        """
        return list(self._plugins.values())

    def is_active(self, name: str) -> bool:
        """Check if a plugin is active."""
        plugin = self._plugins.get(name)
        return plugin["active"] if plugin else False

    def activate(self, name: str) -> None:
        """Activate a plugin."""
        if name in self._plugins:
            self._plugins[name]["active"] = True

    def deactivate(self, name: str) -> None:
        """Deactivate a plugin."""
        if name in self._plugins:
            self._plugins[name]["active"] = False

    def add_hook(self, event_name: str, callback: Callable) -> None:
        """Add a callback listener hook."""
        if event_name not in self._hooks:
            self._hooks[event_name] = []
        self._hooks[event_name].append(callback)

    def remove_hook(self, event_name: str, callback: Callable = None) -> None:
        """Remove one hook callback, or every callback for the event."""
        if callback is None:
            self._hooks.pop(event_name, None)
        elif event_name in self._hooks:
            self._hooks[event_name] = [
                hook for hook in self._hooks[event_name] if hook is not callback
            ]

    def has_hook(self, event_name: str) -> bool:
        return bool(self._hooks.get(event_name))

    def trigger_hook(self, event_name: str, *args, **kwargs) -> List[Any]:
        """Trigger every callback registered for a hook.

        One misbehaving plugin must not take down the request, so failures are
        isolated — but they are logged, not swallowed. A plugin that throws on
        every call used to be completely invisible.
        """
        results: List[Any] = []
        for callback in self._hooks.get(event_name, []):
            try:
                results.append(callback(*args, **kwargs))
            except Exception:
                import logging

                logging.getLogger("craft").warning(
                    "Plugin hook '%s' raised in %s",
                    event_name,
                    getattr(callback, "__qualname__", repr(callback)),
                    exc_info=True,
                )
        return results

    # -- disk discovery ----------------------------------------------------

    def discover(self, base_path: str) -> List[dict]:
        """Scan `<base_path>/plugins/*/plugin.py` for plugin descriptors.

        Each plugin directory is expected to expose a `PLUGIN` dict with at
        least `slug` and `name`. Directories without a `plugin.py`, or whose
        module fails to import, or whose `PLUGIN` dict is missing/malformed
        are skipped — one broken plugin must not stop discovery of the rest.
        Returns the list of descriptors found, each augmented with the
        on-disk `path` it was discovered at. This does not touch the DB.
        """
        plugins_dir = os.path.join(base_path, "plugins")
        found: List[dict] = []

        if not os.path.isdir(plugins_dir):
            return found

        for entry in sorted(os.listdir(plugins_dir)):
            plugin_dir = os.path.join(plugins_dir, entry)
            manifest_path = os.path.join(plugin_dir, "plugin.py")
            if not os.path.isdir(plugin_dir) or not os.path.isfile(manifest_path):
                continue

            try:
                spec = importlib.util.spec_from_file_location(
                    f"craft_plugin_{entry}", manifest_path
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            except Exception:
                import logging

                logging.getLogger("craft").warning(
                    "Failed to load plugin manifest at %s", manifest_path, exc_info=True
                )
                continue

            descriptor = getattr(module, "PLUGIN", None)
            if not isinstance(descriptor, dict) or not descriptor.get("slug"):
                continue

            found.append({
                "slug": descriptor["slug"],
                "name": descriptor.get("name", descriptor["slug"]),
                "version": descriptor.get("version", "1.0.0"),
                "description": descriptor.get("description", ""),
                "path": plugin_dir,
            })

        return found

    # -- DB-backed state, mirroring services.modules.manager.ModuleManager --

    def installed(self) -> List[dict]:
        """Fetch all disk-discovered plugins persisted in DB or memory."""
        try:
            res = DB.statement("SELECT slug, name, enabled, path FROM plugins")
            rows = res.fetchall()
            if rows:
                # Access by column name: SQLite rows are sqlite3.Row and the
                # MySQL/PostgreSQL cursors return dicts — positional indexing
                # raises KeyError on those drivers.
                return [
                    {
                        "slug": r["slug"],
                        "name": r["name"],
                        "enabled": bool(r["enabled"]),
                        "path": r["path"],
                    }
                    for r in rows
                ]
        except Exception:
            pass
        return list(self._registered_slugs.values())

    def is_enabled(self, slug: str) -> bool:
        """Check if a plugin is enabled."""
        try:
            res = DB.statement("SELECT enabled FROM plugins WHERE slug = :slug", {"slug": slug})
            row = res.fetchone()
            if row is not None:
                return bool(row["enabled"])
        except Exception:
            pass
        plugin = self._registered_slugs.get(slug)
        return plugin["enabled"] if plugin else False

    def _set_enabled(self, slug: str, enabled: bool) -> bool:
        """Flip a plugin's state. Returns whether the plugin was found."""
        affected = 0
        try:
            result = DB.statement(
                "UPDATE plugins SET enabled = :enabled WHERE slug = :slug",
                {"enabled": enabled, "slug": slug},
            )
            affected = getattr(result, "rowcount", 0) or 0
        except Exception:
            affected = 0

        in_memory = slug in self._registered_slugs
        if in_memory:
            self._registered_slugs[slug]["enabled"] = enabled

        # Report what actually happened. Returning True unconditionally would
        # make "enable a plugin that does not exist" look like a success —
        # ModuleManager had exactly this bug; not reintroducing it here.
        return affected > 0 or in_memory

    def enable(self, slug: str) -> bool:
        """Enable a plugin. Returns False when there is no such plugin."""
        return self._set_enabled(slug, True)

    def disable(self, slug: str) -> bool:
        """Disable a plugin. Returns False when there is no such plugin."""
        return self._set_enabled(slug, False)

    def register_slug(self, slug: str, name: str, path: str = None) -> None:
        """Register a disk-discovered plugin in memory (fallback path)."""
        self._registered_slugs[slug] = {
            "slug": slug,
            "name": name,
            "enabled": True,
            "path": path,
        }

    def sync(self, base_path: str) -> List[str]:
        """Discover plugins under `base_path` and upsert new ones into the DB.

        Existing rows are left alone — re-syncing must not silently re-enable
        a plugin an operator disabled. Returns the slugs that were newly
        registered.
        """
        discovered = self.discover(base_path)
        existing_slugs = {p["slug"] for p in self.installed()}

        newly_registered: List[str] = []
        for plugin in discovered:
            if plugin["slug"] in existing_slugs:
                continue

            inserted = False
            try:
                DB.statement(
                    "INSERT INTO plugins (name, slug, enabled, path) VALUES (:name, :slug, :enabled, :path)",
                    {
                        "name": plugin["name"],
                        "slug": plugin["slug"],
                        "enabled": True,
                        "path": plugin["path"],
                    },
                )
                inserted = True
            except Exception:
                inserted = False

            if not inserted:
                self.register_slug(plugin["slug"], plugin["name"], plugin["path"])

            newly_registered.append(plugin["slug"])

        return newly_registered
