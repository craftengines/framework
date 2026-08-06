"""Soft deletes for the Codepyquent ORM.

Mix `SoftDeletes` into a model whose table has a `deleted_at` column. Queries
exclude trashed rows by default; `with_trashed()` / `only_trashed()` opt back in.
"""
# Codepy Framework
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

    # -- query scopes ----------------------------------------------------------

    @classmethod
    def _base_query(cls) -> Any:
        from services.orm.query_builder import QueryBuilder

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
        from services.container.application import Container

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
        from services.container.application import Container

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
        from services.container.application import Container

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
