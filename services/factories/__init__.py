"""Model factories for Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from typing import Any, Dict, List, Optional, Type


class Factory:
    """Base model factory.

    Subclasses set `model` and implement `definition()`. Extra state methods
    returning attribute dicts can be applied via :meth:`state`.
    """

    model: Optional[Type] = None

    def __init__(self, count: int = 1, states: Optional[List[Dict[str, Any]]] = None):
        self._count = count
        self._states: List[Dict[str, Any]] = list(states or [])

    def definition(self) -> Dict[str, Any]:  # pragma: no cover - user supplied
        raise NotImplementedError("Factory must implement definition().")

    # -- fluent configuration --------------------------------------------------

    @classmethod
    def new(cls, count: int = 1) -> "Factory":
        return cls(count=count)

    @classmethod
    def times(cls, count: int) -> "Factory":
        return cls(count=count)

    def count(self, count: int) -> "Factory":
        self._count = count
        return self

    def state(self, attributes: Any) -> "Factory":
        """Apply a state: a dict, or the name of a state method on the factory."""
        if isinstance(attributes, str):
            method = getattr(self, attributes, None)
            if not callable(method):
                raise AttributeError(f"Factory has no state [{attributes}].")
            attributes = method()
        self._states.append(dict(attributes or {}))
        return self

    # -- building --------------------------------------------------------------

    def raw(self, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        attributes = dict(self.definition())
        for state in self._states:
            attributes.update(state)
        attributes.update(overrides or {})
        return attributes

    def make(self, overrides: Optional[Dict[str, Any]] = None) -> Any:
        """Build unsaved model instances."""
        if self.model is None:
            raise RuntimeError(f"{type(self).__name__}.model is not set.")
        instances = [self.model(self.raw(overrides)) for _ in range(self._count)]
        return instances[0] if self._count == 1 else instances

    def create(self, overrides: Optional[Dict[str, Any]] = None) -> Any:
        """Persist model instances to the database."""
        if self.model is None:
            raise RuntimeError(f"{type(self).__name__}.model is not set.")
        instances = [self.model.create(self.raw(overrides)) for _ in range(self._count)]
        return instances[0] if self._count == 1 else instances


__all__ = ["Factory"]
