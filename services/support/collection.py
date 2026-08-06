"""Collection and Helper utilities for Codepy Framework."""

from typing import Any, Callable, Dict, List, Optional, Union


class Collection:
    """Laravel-style collection class for chainable data operations."""

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


def __(key: str, locale: Optional[str] = None) -> str:
    """Translation helper function with DB fallback."""
    from services.container.application import Container
    try:
        app = Container.getInstance()
        config = app.make("config")
        lang = locale or config.get("app.locale", "en")

        # 1. Check Config
        val = config.get(f"lang.{lang}.{key}")
        if val:
            return str(val)

        # 2. Check DB translations table if present
        db = app.make("db")
        res = db.statement("SELECT value FROM translations WHERE key = ? AND locale = ?", [key, lang], read=True)
        row = res.fetchone()
        if row:
            return str(row[0])
    except Exception:
        pass
    return key
