"""
Collection — Chainable wrapper around a list (map/filter/reduce-style helpers).
Category: Core Framework (Support).
Relations:
  - Returned by `QueryBuilder.get()` (`engine/orm/query_builder.py`) and
    `Model.all()`.
References:
  - Guide: `documentation/orm.md#querying--filtering`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from typing import Any, Callable, Dict, List, Optional, Union


class Collection:
    """Chainable collection class."""

    def __init__(self, items: Optional[List[Any]] = None):
        self._items = list(items) if items is not None else []

    def all(self) -> List[Any]:
        return self._items

    def count(self) -> int:
        return len(self._items)

    def first(self) -> Any:
        return self._items[0] if self._items else None

    def last(self) -> Any:
        return self._items[-1] if self._items else None

    def map(self, callback: Callable) -> 'Collection':
        return Collection([callback(item) for item in self._items])

    def filter(self, callback: Callable) -> 'Collection':
        return Collection([item for item in self._items if callback(item)])

    def pluck(self, key: str) -> 'Collection':
        results = []
        for item in self._items:
            if isinstance(item, dict):
                results.append(item.get(key))
            elif hasattr(item, key):
                results.append(getattr(item, key))
            elif hasattr(item, "get_attribute"):
                results.append(item.get_attribute(key))
        return Collection(results)

    def to_dict(self) -> List[Any]:
        return [
            item.to_dict() if hasattr(item, "to_dict")
            else item.to_array() if hasattr(item, "to_array")
            else item
            for item in self._items
        ]

    def __len__(self) -> int:
        return len(self._items)

    def __getitem__(self, index: int) -> Any:
        return self._items[index]

    def __iter__(self):
        return iter(self._items)


# The translation helper lives in `engine.support.translation`; re-exported
# here so `from craft.support.collection import __` keeps working.
from engine.support.translation import __, translate  # noqa: E402,F401
