"""
Navigation — the menu as data, filtered by what each visitor may actually reach.
Category: Core Framework (Support).
Relations:
  - Bound in the container as `nav`, exposed via the `Nav` facade. The
    application declares its menu in a service provider
    (`app/Providers/PanelServiceProvider.py`).
  - Every guard is delegated: roles, groups and permissions go to
    `engine/auth/access.py`, abilities to `engine/auth/gate.py`, and module
    switches to `engine/modules/manager.py`. Nothing here re-decides access.
References:
  - Guide: `documentation/authorization.md`, `documentation/views.md`

Why this exists: a menu hardcoded in a template is a second, silent
authorization system. It drifts — offering links the visitor cannot open (an
invitation to a 403, which is exactly what happened with the admin Dashboard
button), or hiding pages they are entitled to. Declaring each item with the
same guard the route carries keeps the menu and the router describing one
reality.

    Nav.section("content", "Content", icon="document", order=20)
    Nav.add("content", "Posts", "/panel/posts", icon="document")
    Nav.add("system", "Modules", "/panel/modules", icon="squares",
            role="admin", module="inventory")
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

_LOG = logging.getLogger("craft")


class NavItem:
    """One link, plus the conditions under which it is shown.

    Every condition must pass (AND). All of them are optional — an item with no
    conditions is visible to anyone who can see the menu at all.
    """

    __slots__ = (
        "label", "url", "icon", "section", "order", "badge",
        "permission", "role", "group", "ability", "module", "visible_when",
    )

    def __init__(
        self,
        label: str,
        url: str,
        *,
        icon: str = "dot",
        section: str = "main",
        order: int = 100,
        badge: Optional[Any] = None,
        permission: Optional[str] = None,
        role: Optional[str] = None,
        group: Optional[str] = None,
        ability: Optional[str] = None,
        module: Optional[str] = None,
        visible_when: Optional[Any] = None,
    ):
        self.label = label
        self.url = url
        self.icon = icon
        self.section = section
        self.order = order
        #: Either a value or a zero-argument callable, resolved at render time.
        self.badge = badge
        self.permission = permission
        self.role = role
        self.group = group
        self.ability = ability
        self.module = module
        #: Escape hatch: `callable(user) -> bool` for anything the declarative
        #: fields cannot express.
        self.visible_when = visible_when

    def to_dict(self, active: bool = False) -> Dict[str, Any]:
        badge = self.badge
        if callable(badge):
            try:
                badge = badge()
            except Exception:
                # A counter that fails must not take the whole menu with it.
                badge = None
        return {
            "label": self.label,
            "url": self.url,
            "icon": self.icon,
            "badge": badge,
            "active": active,
        }

    def match_length(self, path: str) -> int:
        """How well this item matches the current path; 0 means not at all.

        Used to pick a single winner: an exact match scores highest, and a
        prefix match scores by how much of the path it covers. Without this,
        `/panel` lit up on every page beneath it and the sidebar showed two
        items highlighted at once — the menu claiming the visitor is in two
        places.
        """
        if not path or not self.url:
            return 0
        if path == self.url:
            return len(self.url) + 1
        if self.url != "/" and path.startswith(self.url.rstrip("/") + "/"):
            return len(self.url.rstrip("/"))
        return 0


class NavSection:
    """A titled group of items, e.g. "Content" or "Administration"."""

    __slots__ = ("key", "title", "order", "items")

    def __init__(self, key: str, title: str, order: int = 100):
        self.key = key
        self.title = title
        self.order = order
        self.items: List[NavItem] = []


class Navigation:
    """The menu registry. Declare once at boot; resolve per request."""

    def __init__(self, app: Any = None):
        self.app = app
        self._sections: Dict[str, NavSection] = {}

    # -- declaration -----------------------------------------------------------

    def section(self, key: str, title: str = "", order: int = 100) -> "Navigation":
        """Create (or retitle) a section. Sections render in `order`."""
        existing = self._sections.get(key)
        if existing is None:
            self._sections[key] = NavSection(key, title or key.title(), order)
        else:
            existing.title = title or existing.title
            existing.order = order
        return self

    def add(self, section: str, label: str, url: str, **options) -> "Navigation":
        """Add an item to a section, creating the section if needed."""
        if section not in self._sections:
            self.section(section, section.replace("-", " ").title())
        options.setdefault("section", section)
        self._sections[section].items.append(NavItem(label, url, **options))
        return self

    def clear(self) -> None:
        """Drop every section and item — for tests, and for re-declaration."""
        self._sections.clear()

    # -- resolution ------------------------------------------------------------

    def _access(self):
        if self.app is None:
            return None
        try:
            return self.app.make("access")
        except Exception:
            return None

    def _module_enabled(self, slug: str) -> bool:
        if self.app is None:
            return False
        try:
            state = self.app.make("module").state(slug)
        except Exception:
            return False
        if state is None:
            # Unknown to the manager: fall back to config, which defaults to
            # enabled — the same rule the router applies to `.module()` routes,
            # so a menu item and its route cannot disagree.
            try:
                return bool(self.app.make("config").get(f"modules.{slug}.enabled", True))
            except Exception:
                return False
        return state

    def allows(self, item: NavItem, user: Any) -> bool:
        """Whether this visitor should see this item.

        Denies on any error. A menu is not the place to be optimistic: showing
        a link the visitor cannot open is how someone ends up staring at a 403
        they did nothing to deserve.
        """
        try:
            if item.module and not self._module_enabled(item.module):
                return False

            if item.permission or item.role or item.group:
                access = self._access()
                if access is None or user is None:
                    return False
                if item.role and not access.has_role(user, item.role):
                    return False
                if item.group and not access.in_group(user, item.group):
                    return False
                if item.permission and not access.allows(user, item.permission):
                    return False

            if item.ability:
                if user is None:
                    return False
                gate = self.app.make("gate") if self.app is not None else None
                if gate is None or not gate.allows(item.ability, user):
                    return False

            if item.visible_when is not None and not item.visible_when(user):
                return False
        except Exception:
            _LOG.warning(
                "Could not evaluate visibility for menu item %r; hiding it.",
                item.label, exc_info=True,
            )
            return False
        return True

    def for_user(self, user: Any, active_path: str = "") -> List[Dict[str, Any]]:
        """The menu this visitor should see, as plain data for a template.

        Sections with no visible items are dropped, so an ordinary account does
        not stare at an empty "Administration" heading.
        """
        visible = [
            (section, [item for item in sorted(section.items, key=lambda i: (i.order, i.label))
                       if self.allows(item, user)])
            for section in sorted(self._sections.values(), key=lambda s: (s.order, s.title))
        ]

        # Exactly one item is active: the one matching the current path best.
        # Deciding this across the whole menu, rather than per item, is what
        # stops a parent like `/panel` from lighting up alongside `/panel/access`.
        best_item = None
        best_score = 0
        for _, items in visible:
            for item in items:
                score = item.match_length(active_path)
                if score > best_score:
                    best_item, best_score = item, score

        rendered: List[Dict[str, Any]] = []
        for section, items in visible:
            if not items:
                continue
            rendered.append({
                "key": section.key,
                "title": section.title,
                "items": [item.to_dict(item is best_item) for item in items],
            })
        return rendered


__all__ = ["Navigation", "NavItem", "NavSection"]
