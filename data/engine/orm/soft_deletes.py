"""Soft deletes for the Craft ORM.

Mix `SoftDeletes` into a model whose table has a `deleted_at` column. Queries
exclude trashed rows by default; `with_trashed()` / `only_trashed()` opt back in.

Category: Core Framework (ORM).
Relations:
  - Mixed in before `Model` in a subclass's bases — list order matters, or
    the MRO makes `Model` win (`class Note(SoftDeletes, Model)`).
References:
  - Guide: `documentation/orm.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat()


class SoftDeletes:
    """Model mixin providing trash / restore semantics.

    List the mixin FIRST so its `query()` and `delete()` win the MRO::

        class Note(SoftDeletes, Model):
            __table__ = "notes"

    The scopes below build their own QueryBuilder rather than calling
    `super().query()`, so a model that lists the bases the other way round
    still gets working `with_trashed()` / `only_trashed()` helpers instead of
    an AttributeError.
    """

    deleted_at_column: str = "deleted_at"

    def __init_subclass__(cls, **kwargs):
        """Refuse to let the bases be listed in the order that silently breaks.

        With `class Note(Model, SoftDeletes)` the MRO gives `Model.delete()`,
        so `note.delete()` issues a real DELETE while the model advertises soft
        deletes — data destroyed by a call the developer believed was
        reversible. It used to be a documentation footnote; the failure mode is
        too quiet and too expensive for that.
        """
        super().__init_subclass__(**kwargs)

        mro = cls.__mro__
        model_class = next(
            (base for base in mro if base.__name__ == "Model"), None
        )
        if model_class is None:
            return

        if mro.index(model_class) < mro.index(SoftDeletes):
            raise TypeError(
                f"{cls.__name__} lists SoftDeletes after Model, so Model.delete() "
                f"wins the MRO and deletes rows permanently. Write "
                f"`class {cls.__name__}(SoftDeletes, Model)` instead."
            )

    # -- query scopes ----------------------------------------------------------

    @classmethod
    def _base_query(cls) -> Any:
        from engine.orm.query_builder import QueryBuilder

        return QueryBuilder(model_class=cls)

    @classmethod
    def query(cls) -> Any:
        """Default query — excludes soft-deleted rows."""
        return cls._base_query().where_null(cls.deleted_at_column)

    @classmethod
    def with_trashed(cls) -> Any:
        """Include soft-deleted rows."""
        return cls._base_query()

    @classmethod
    def only_trashed(cls) -> Any:
        """Only soft-deleted rows."""
        return cls._base_query().where_not_null(cls.deleted_at_column)

    # -- instance operations ---------------------------------------------------

    def delete(self) -> bool:
        """Soft delete: stamp `deleted_at` instead of removing the row."""
        from engine.container.application import Container

        key = self.primary_key
        if self._attributes.get(key) is None:
            return False

        stamp = _now()
        db = Container.getInstance().make("db")
        db.statement(
            f"UPDATE {self.get_table_name()} SET {self.deleted_at_column} = ? WHERE {key} = ?",
            [stamp, self._attributes[key]],
        )
        self._attributes[self.deleted_at_column] = stamp
        return True

    def force_delete(self) -> bool:
        """Permanently remove the row."""
        from engine.container.application import Container

        key = self.primary_key
        if self._attributes.get(key) is None:
            return False
        db = Container.getInstance().make("db")
        db.statement(
            f"DELETE FROM {self.get_table_name()} WHERE {key} = ?", [self._attributes[key]]
        )
        return True

    def restore(self) -> bool:
        """Undo a soft delete."""
        from engine.container.application import Container

        key = self.primary_key
        if self._attributes.get(key) is None:
            return False
        db = Container.getInstance().make("db")
        db.statement(
            f"UPDATE {self.get_table_name()} SET {self.deleted_at_column} = NULL WHERE {key} = ?",
            [self._attributes[key]],
        )
        self._attributes[self.deleted_at_column] = None
        return True

    def trashed(self) -> bool:
        return self._attributes.get(self.deleted_at_column) is not None


__all__ = ["SoftDeletes"]
