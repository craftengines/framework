"""Relationships for the Craft ORM.

Each relation wraps a QueryBuilder, so the whole builder API (where, order_by,
paginate, aggregates) is available on a relationship before it is resolved.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Type


def _unique(values: Iterable[Any]) -> List[Any]:
    """Distinct, non-null, order-preserving — the keys for an eager IN clause."""
    seen = set()
    result = []
    for value in values:
        if value is None or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


class Relation:
    """Base relation. Unknown attributes proxy to the underlying query.

    Relations also know how to resolve a whole batch of parents in a single
    query — see `eager_keys()` / `eager_query()` / `match()`, which the query
    builder's `with_()` drives to avoid N+1.
    """

    def __init__(self, parent: Any, related_class: Type, name: Optional[str] = None):
        self.parent = parent
        self.related_class = related_class
        #: Name of the model method that built this relation ("posts"), used to
        #: read and write the parent's eager-loaded cache.
        self.name = name

    def query(self) -> Any:  # pragma: no cover - overridden
        raise NotImplementedError

    # -- eager loading (overridden per relation type) --------------------------

    def eager_keys(self, models: List[Any]) -> List[Any]:  # pragma: no cover
        raise NotImplementedError

    def eager_query(self, keys: List[Any]) -> Any:  # pragma: no cover
        raise NotImplementedError

    def match(self, models: List[Any], results: Any) -> None:  # pragma: no cover
        raise NotImplementedError

    def _cached(self) -> Any:
        """Return the eager-loaded value for this relation, if there is one."""
        if self.name and self.parent.relation_loaded(self.name):
            return self.parent.get_relation(self.name)
        return _NOT_LOADED

    # -- resolution ------------------------------------------------------------

    def get(self) -> Any:
        cached = self._cached()
        return self.query().get() if cached is _NOT_LOADED else cached

    def first(self) -> Any:
        cached = self._cached()
        if cached is _NOT_LOADED:
            return self.query().first()
        if cached is None or not hasattr(cached, "__len__"):
            return cached
        return cached[0] if len(cached) else None

    def count(self) -> int:
        cached = self._cached()
        if cached is _NOT_LOADED:
            return self.query().count()
        if cached is None:
            return 0
        return len(cached) if hasattr(cached, "__len__") else 1

    def exists(self) -> bool:
        return self.count() > 0

    def __len__(self) -> int:
        return self.count()

    def __iter__(self):
        return iter(self.get())

    def __getattr__(self, name: str):
        # Proxy builder methods (where, order_by, limit, paginate, ...).
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(self.query(), name)


class _NotLoaded:
    """Sentinel distinguishing "not eager loaded" from a loaded `None`."""

    def __repr__(self) -> str:
        return "<not loaded>"


_NOT_LOADED = _NotLoaded()


class HasMany(Relation):
    """One-to-many: `user.posts()` -> posts where user_id = user.id."""

    def __init__(
        self,
        parent: Any,
        related_class: Type,
        foreign_key: str,
        local_key: str = "id",
        name: Optional[str] = None,
    ):
        super().__init__(parent, related_class, name)
        self.foreign_key = foreign_key
        self.local_key = local_key

    def query(self) -> Any:
        return self.related_class.query().where(
            self.foreign_key, self.parent.get_attribute(self.local_key)
        )

    def create(self, attributes: Dict[str, Any]) -> Any:
        attributes = dict(attributes)
        attributes[self.foreign_key] = self.parent.get_attribute(self.local_key)
        return self.related_class.create(attributes)

    # -- eager loading ---------------------------------------------------------

    def eager_keys(self, models: List[Any]) -> List[Any]:
        return _unique(m.get_attribute(self.local_key) for m in models)

    def eager_query(self, keys: List[Any]) -> Any:
        return self.related_class.query().where_in(self.foreign_key, keys).get()

    def _group(self, results: Any) -> Dict[Any, List[Any]]:
        grouped: Dict[Any, List[Any]] = {}
        for related in results:
            grouped.setdefault(related.get_attribute(self.foreign_key), []).append(related)
        return grouped

    def match(self, models: List[Any], results: Any) -> None:
        from services.support.collection import Collection

        grouped = self._group(results)
        for model in models:
            children = grouped.get(model.get_attribute(self.local_key), [])
            model.set_relation(self.name, Collection(children))


class HasOne(HasMany):
    """One-to-one — same keys as HasMany, resolved to a single record."""

    def get(self) -> Any:
        return self.first()

    def match(self, models: List[Any], results: Any) -> None:
        grouped = self._group(results)
        for model in models:
            children = grouped.get(model.get_attribute(self.local_key), [])
            model.set_relation(self.name, children[0] if children else None)


class BelongsTo(Relation):
    """Inverse one-to-many: `post.user()` -> users where id = post.user_id."""

    def __init__(
        self,
        parent: Any,
        related_class: Type,
        foreign_key: str,
        owner_key: str = "id",
        name: Optional[str] = None,
    ):
        super().__init__(parent, related_class, name)
        self.foreign_key = foreign_key
        self.owner_key = owner_key

    def query(self) -> Any:
        return self.related_class.query().where(
            self.owner_key, self.parent.get_attribute(self.foreign_key)
        )

    def get(self) -> Any:
        return self.first()

    # -- eager loading ---------------------------------------------------------

    def eager_keys(self, models: List[Any]) -> List[Any]:
        return _unique(m.get_attribute(self.foreign_key) for m in models)

    def eager_query(self, keys: List[Any]) -> Any:
        return self.related_class.query().where_in(self.owner_key, keys).get()

    def match(self, models: List[Any], results: Any) -> None:
        owners = {r.get_attribute(self.owner_key): r for r in results}
        for model in models:
            model.set_relation(self.name, owners.get(model.get_attribute(self.foreign_key)))

    def associate(self, model: Any) -> Any:
        self.parent.set_attribute(self.foreign_key, model.get_attribute(self.owner_key))
        return self.parent

    def dissociate(self) -> Any:
        self.parent.set_attribute(self.foreign_key, None)
        return self.parent


class BelongsToMany(Relation):
    """Many-to-many through a pivot table (`role_user`, `permission_role`)."""

    def __init__(
        self,
        parent: Any,
        related_class: Type,
        pivot_table: str,
        foreign_pivot_key: str,
        related_pivot_key: str,
        parent_key: str = "id",
        related_key: str = "id",
        name: Optional[str] = None,
    ):
        super().__init__(parent, related_class, name)
        self.pivot_table = pivot_table
        self.foreign_pivot_key = foreign_pivot_key
        self.related_pivot_key = related_pivot_key
        self.parent_key = parent_key
        self.related_key = related_key

    def query(self) -> Any:
        related_table = self.related_class.get_table_name()
        return (
            self.related_class.query()
            .select(f"{related_table}.*")
            .join(
                self.pivot_table,
                f"{related_table}.{self.related_key}",
                "=",
                f"{self.pivot_table}.{self.related_pivot_key}",
            )
            .where(
                f"{self.pivot_table}.{self.foreign_pivot_key}",
                self.parent.get_attribute(self.parent_key),
            )
        )

    # -- eager loading ---------------------------------------------------------

    #: Alias the pivot's owner column into the result set so a batched query can
    #: tell which parent each related row belongs to.
    PIVOT_KEY_ALIAS = "_pivot_owner_key"

    def eager_keys(self, models: List[Any]) -> List[Any]:
        return _unique(m.get_attribute(self.parent_key) for m in models)

    def eager_query(self, keys: List[Any]) -> Any:
        related_table = self.related_class.get_table_name()
        return (
            self.related_class.query()
            .select(
                f"{related_table}.*",
                f"{self.pivot_table}.{self.foreign_pivot_key} AS {self.PIVOT_KEY_ALIAS}",
            )
            .join(
                self.pivot_table,
                f"{related_table}.{self.related_key}",
                "=",
                f"{self.pivot_table}.{self.related_pivot_key}",
            )
            .where_in(f"{self.pivot_table}.{self.foreign_pivot_key}", keys)
            .get()
        )

    def match(self, models: List[Any], results: Any) -> None:
        from services.support.collection import Collection

        grouped: Dict[Any, List[Any]] = {}
        for related in results:
            grouped.setdefault(related.get_attribute(self.PIVOT_KEY_ALIAS), []).append(related)

        for model in models:
            children = grouped.get(model.get_attribute(self.parent_key), [])
            model.set_relation(self.name, Collection(children))

    def attach(self, related_id: Any) -> None:
        from services.container.application import Container

        db = Container.getInstance().make("db")
        db.statement(
            f"INSERT INTO {self.pivot_table} ({self.foreign_pivot_key}, {self.related_pivot_key}) "
            f"VALUES (?, ?)",
            [self.parent.get_attribute(self.parent_key), related_id],
        )

    def detach(self, related_id: Optional[Any] = None) -> None:
        from services.container.application import Container

        db = Container.getInstance().make("db")
        parent_id = self.parent.get_attribute(self.parent_key)
        if related_id is None:
            db.statement(
                f"DELETE FROM {self.pivot_table} WHERE {self.foreign_pivot_key} = ?", [parent_id]
            )
        else:
            db.statement(
                f"DELETE FROM {self.pivot_table} "
                f"WHERE {self.foreign_pivot_key} = ? AND {self.related_pivot_key} = ?",
                [parent_id, related_id],
            )

    def sync(self, related_ids: List[Any]) -> None:
        self.detach()
        for related_id in related_ids:
            self.attach(related_id)


__all__ = ["Relation", "HasOne", "HasMany", "BelongsTo", "BelongsToMany"]
