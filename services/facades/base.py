"""Base Facade class for Craft Framework with FacadeMeta metaclass."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from typing import Any, Optional


class FacadeMeta(type):
    """Metaclass intercepting static method calls on Facades."""

    def __getattr__(cls, name: str) -> Any:
        # Never fabricate dunder or private attributes. Introspection — pytest
        # collection, inspect, copy, pickle — probes names like `__wrapped__`
        # and `__test__` on module-level objects. Forwarding those to the
        # container resolves it far too early: before the application boots,
        # `Container.getInstance()` builds an empty fallback container and
        # claims the global, so the real app's bindings are never visible.
        if name.startswith("_"):
            raise AttributeError(
                f"{cls.__name__} facade has no attribute '{name}'."
            )

        from services.container.application import Container

        app = getattr(cls, "_app", None) or Container.getInstance()
        service = app.make(cls.get_facade_accessor())
        return getattr(service, name)


class Facade(metaclass=FacadeMeta):
    """Base class for expressive static Facades resolving from IoC Container."""

    _app: Any = None

    @classmethod
    def get_facade_accessor(cls) -> str:
        raise NotImplementedError("Facade must implement get_facade_accessor().")

    @classmethod
    def _clear_resolved(cls) -> None:
        pass

    @classmethod
    def _swap(cls, instance: Any) -> None:
        pass
