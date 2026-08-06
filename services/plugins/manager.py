"""
PluginManager — Third-party plugins discovery and lifecycle management.
Category: Subsystem (Core Framework).
Relations:
  - Registers, boots, and triggers hooks across third-party framework plugins.
References:
  - Skill: `codepy-development` ([SKILL.md](file:///d:/data/www/codepy/.agents/skills/codepy-development/SKILL.md))
"""
# Codepy Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from typing import Callable, Dict, List, Any


class PluginManager:
    """Manages external framework plugins, hooks, and extensions."""

    def __init__(self):
        self._plugins: Dict[str, dict] = {}
        self._hooks: Dict[str, List[Callable]] = {}

    def register(self, name: str, plugin_class_or_dict: Any) -> None:
        """Register a new plugin."""
        self._plugins[name] = {
            "name": name,
            "instance": plugin_class_or_dict,
            "active": True
        }

    def all(self) -> List[dict]:
        """List all registered plugins."""
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

                logging.getLogger("codepy").warning(
                    "Plugin hook '%s' raised in %s",
                    event_name,
                    getattr(callback, "__qualname__", repr(callback)),
                    exc_info=True,
                )
        return results
