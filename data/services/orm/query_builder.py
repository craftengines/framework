"""
QueryBuilder — Fluent, chainable SQL query builder for Craft ORM.
Category: Core Framework (ORM).
Relations:
  - Built by `Model.query()` (`services/orm/model.py`); powers relationship
    proxies (`services/orm/relationships.py`).
  - Executes through `services/orm/connection.py` via the `DatabaseManager`
    (`services/orm/db.py`), never SQLAlchemy.
References:
  - Guide: `documentation/orm.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import inspect
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Type

#: Sentinel telling `where()` apart from an explicit `None` value.
_MISSING = object()

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")

#: Operators `_compile_wheres` will interpolate into SQL.
_ALLOWED_OPERATORS = {
    "=", "!=", "<>", "<", "<=", ">", ">=",
    "LIKE", "NOT LIKE", "IN", "NOT IN", "IS", "IS NOT", "BETWEEN",
}


def _assert_identifier(name: str) -> str:
    """Reject column/table names that could smuggle SQL into a query."""
    if not isinstance(name, str) or not _IDENTIFIER_RE.match(name):
        raise ValueError(f"Invalid SQL identifier [{name!r}].")
    return name


#: `select()` additionally allows a bare "*", a "table.*" wildcard, and a
#: "table.column AS alias" projection — all developer-authored shapes used
#: internally for eager-loaded pivot columns (see relationships.py).
_SELECT_ITEM_RE = re.compile(
    r"^\*$"
    r"|^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*(\.\*)?$"
    r"|^[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*\s+AS\s+[A-Za-z_][A-Za-z0-9_]*$",
    re.IGNORECASE,
)

#: `having()` additionally allows a simple aggregate call, e.g. `COUNT(*)`.
_HAVING_COLUMN_RE = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$"
    r"|^[A-Za-z_]+\((\*|[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*)\)$",
    re.IGNORECASE,
)


def _assert_select_item(item: str) -> str:
    if not isinstance(item, str) or not _SELECT_ITEM_RE.match(item):
        raise ValueError(f"Invalid SQL select expression [{item!r}].")
    return item


def _assert_having_column(column: str) -> str:
    if not isinstance(column, str) or not _HAVING_COLUMN_RE.match(column):
        raise ValueError(f"Invalid SQL having expression [{column!r}].")
    return column


class QueryBuilder:
    """Fluent SQL query builder backed by the application's DatabaseManager."""

    def __init__(
        self,
        model_class: Optional[Type] = None,
        table_name: Optional[str] = None,
        db: Optional[Any] = None,
    ):
        self.model_class = model_class
        self.table_name = table_name or (
            model_class.get_table_name() if model_class else "items"
        )

        if db is not None:
            self.db = db
        else:
            from services.container.application import Container

            try:
                self.db = Container.getInstance().make("db")
            except Exception:
                from services.orm.db import DatabaseManager

                self.db = DatabaseManager()

        self._columns: List[str] = ["*"]
        self._wheres: List[Dict[str, Any]] = []
        self._joins: List[str] = []
        self._group_by: List[str] = []
        self._having: List[Dict[str, Any]] = []
        self._orders: List[str] = []
        self._limit: Optional[int] = None
        self._offset: Optional[int] = None
        self._scopes: List[str] = []
        self._distinct = False
        self._eager: List[str] = []

    # -- selection -------------------------------------------------------------

    def select(self, *columns: str) -> "QueryBuilder":
        for column in columns:
            _assert_select_item(column)
        self._columns = list(columns) or ["*"]
        return self

    def distinct(self) -> "QueryBuilder":
        self._distinct = True
        return self

    # -- where clauses ---------------------------------------------------------

    def where(self, column: str, operator_or_value: Any = _MISSING, value: Any = _MISSING) -> "QueryBuilder":
        _assert_identifier(column)
        if value is _MISSING:
            op, val = "=", operator_or_value
        else:
            op, val = operator_or_value, value

        if val is None:
            # `col = None` never matches in SQL — route to IS (NOT) NULL.
            if op == "=":
                return self.where_null(column)
            if op in ("!=", "<>"):
                return self.where_not_null(column)
            raise ValueError(f"Cannot compare with None using operator [{op}].")

        self._wheres.append({"boolean": "AND", "column": column, "operator": op, "value": val})
        return self

    def or_where(self, column: str, operator_or_value: Any = _MISSING, value: Any = _MISSING) -> "QueryBuilder":
        self.where(column, operator_or_value, value)
        self._wheres[-1]["boolean"] = "OR"
        return self

    def where_in(self, column: str, values: Sequence[Any]) -> "QueryBuilder":
        _assert_identifier(column)
        self._wheres.append({"boolean": "AND", "column": column, "type": "in", "value": list(values)})
        return self

    def where_not_in(self, column: str, values: Sequence[Any]) -> "QueryBuilder":
        _assert_identifier(column)
        self._wheres.append({"boolean": "AND", "column": column, "type": "not_in", "value": list(values)})
        return self

    def where_null(self, column: str) -> "QueryBuilder":
        _assert_identifier(column)
        self._wheres.append({"boolean": "AND", "column": column, "type": "null"})
        return self

    def where_not_null(self, column: str) -> "QueryBuilder":
        _assert_identifier(column)
        self._wheres.append({"boolean": "AND", "column": column, "type": "not_null"})
        return self

    def where_between(self, column: str, low: Any, high: Any) -> "QueryBuilder":
        _assert_identifier(column)
        self._wheres.append({"boolean": "AND", "column": column, "type": "between", "value": [low, high]})
        return self

    def where_like(self, column: str, pattern: str) -> "QueryBuilder":
        return self.where(column, "LIKE", pattern)

    # -- joins / grouping ------------------------------------------------------

    def join(self, table: str, first: str, operator: str, second: str) -> "QueryBuilder":
        _assert_identifier(table)
        _assert_identifier(first)
        _assert_identifier(second)
        if operator.upper() not in _ALLOWED_OPERATORS:
            raise ValueError(f"Invalid join operator [{operator}].")
        self._joins.append(f"INNER JOIN {table} ON {first} {operator} {second}")
        return self

    def left_join(self, table: str, first: str, operator: str, second: str) -> "QueryBuilder":
        _assert_identifier(table)
        _assert_identifier(first)
        _assert_identifier(second)
        if operator.upper() not in _ALLOWED_OPERATORS:
            raise ValueError(f"Invalid join operator [{operator}].")
        self._joins.append(f"LEFT JOIN {table} ON {first} {operator} {second}")
        return self

    def group_by(self, *columns: str) -> "QueryBuilder":
        for column in columns:
            _assert_identifier(column)
        self._group_by.extend(columns)
        return self

    def having(self, column: str, operator: str, value: Any) -> "QueryBuilder":
        _assert_having_column(column)
        if operator.upper() not in _ALLOWED_OPERATORS:
            raise ValueError(f"Invalid SQL operator [{operator}].")
        self._having.append({"column": column, "operator": operator, "value": value})
        return self

    # -- ordering / paging -----------------------------------------------------

    def order_by(self, column: str, direction: str = "asc") -> "QueryBuilder":
        _assert_identifier(column)
        self._orders.append(f"{column} {'DESC' if direction.lower() == 'desc' else 'ASC'}")
        return self

    def order_by_desc(self, column: str) -> "QueryBuilder":
        return self.order_by(column, "desc")

    def latest(self, column: str = "created_at") -> "QueryBuilder":
        return self.order_by(column, "desc")

    def limit(self, limit: int) -> "QueryBuilder":
        self._limit = limit
        return self

    def offset(self, offset: int) -> "QueryBuilder":
        self._offset = offset
        return self

    take = limit
    skip = offset

    # -- scopes ----------------------------------------------------------------

    def scope(self, scope_name: str, *args: Any) -> "QueryBuilder":
        self._scopes.append(scope_name)
        if self.model_class and hasattr(self.model_class, f"scope_{scope_name}"):
            method = getattr(self.model_class, f"scope_{scope_name}")
            signature = inspect.signature(method)
            params_count = len(signature.parameters)
            if params_count == 1:
                return method(self) or self
            if params_count == 2 and not args:
                return method(self, self) or self
            return method(self, *args) or self
        return self

    # -- compilation -----------------------------------------------------------

    def _compile_wheres(self) -> tuple[str, List[Any]]:
        if not self._wheres:
            return "", []

        combined = ""
        params: List[Any] = []
        for where in self._wheres:
            kind = where.get("type")
            column = where["column"]

            if kind == "in" or kind == "not_in":
                if not where["value"]:
                    condition = f"1 = {'0' if kind == 'in' else '1'}"
                else:
                    placeholders = ", ".join(["?"] * len(where["value"]))
                    keyword = "IN" if kind == "in" else "NOT IN"
                    condition = f"{column} {keyword} ({placeholders})"
                    params.extend(where["value"])
            elif kind == "null":
                condition = f"{column} IS NULL"
            elif kind == "not_null":
                condition = f"{column} IS NOT NULL"
            elif kind == "between":
                condition = f"{column} BETWEEN ? AND ?"
                params.extend(where["value"])
            else:
                operator = str(where["operator"])
                if operator.upper() not in _ALLOWED_OPERATORS:
                    raise ValueError(f"Invalid SQL operator [{operator}].")
                condition = f"{column} {operator} ?"
                params.append(where["value"])

            # Left-associative combination: parenthesising everything built so
            # far before an OR keeps earlier ANDs (soft-delete scopes included)
            # from being bypassed. Pure-AND chains compile exactly as before.
            if not combined:
                combined = condition
            elif where.get("boolean", "AND") == "OR":
                combined = f"({combined}) OR {condition}"
            else:
                combined += f" AND {condition}"

        return " WHERE " + combined, params

    def to_sql(self) -> tuple[str, List[Any]]:
        distinct = "DISTINCT " if self._distinct else ""
        query = f"SELECT {distinct}{', '.join(self._columns)} FROM {self.table_name}"

        for join in self._joins:
            query += f" {join}"

        where_sql, params = self._compile_wheres()
        query += where_sql

        if self._group_by:
            query += " GROUP BY " + ", ".join(self._group_by)

        if self._having:
            parts = []
            for having in self._having:
                parts.append(f"{having['column']} {having['operator']} ?")
                params.append(having["value"])
            query += " HAVING " + " AND ".join(parts)

        if self._orders:
            query += " ORDER BY " + ", ".join(self._orders)

        if self._limit is not None:
            query += f" LIMIT {int(self._limit)}"

        if self._offset is not None:
            query += f" OFFSET {int(self._offset)}"

        return query, params

    # -- execution -------------------------------------------------------------

    def with_(self, *relations: str) -> "QueryBuilder":
        """Eager load relations, turning N+1 queries into one query each.

            posts = Post.query().with_("user").get()
            for post in posts:
                post.user().first()   # already loaded, no query

        Relation names are the model's relation method names.
        """
        self._eager.extend(relations)
        return self

    def without(self, *relations: str) -> "QueryBuilder":
        self._eager = [r for r in self._eager if r not in relations]
        return self

    def _eager_load(self, models: List[Any]) -> None:
        """Resolve each requested relation for the whole batch at once."""
        if not models or not self._eager or not self.model_class:
            return

        for name in dict.fromkeys(self._eager):
            method = getattr(self.model_class, name, None)
            if not callable(method):
                from services.orm.exceptions import RelationNotFoundError

                raise RelationNotFoundError(
                    f"{self.model_class.__name__} has no relation [{name}]."
                )

            relation = method(models[0])
            keys = relation.eager_keys(models)
            results = relation.eager_query(keys) if keys else []
            relation.match(models, results)

    def get(self) -> Any:
        query, params = self.to_sql()
        rows = self.db.statement(query, params, read=True).fetchall()

        results: List[Any] = []
        for row in rows:
            row_dict = dict(row)
            results.append(self.model_class(row_dict) if self.model_class else row_dict)

        self._eager_load(results)

        from services.support.collection import Collection

        return Collection(results)

    def first(self) -> Any:
        previous_limit = self._limit
        self._limit = 1
        try:
            items = self.get()
        finally:
            self._limit = previous_limit
        return items[0] if len(items) > 0 else None

    def find(self, id_val: Any) -> Any:
        key = getattr(self.model_class, "primary_key", "id") if self.model_class else "id"
        return self.where(key, id_val).first()

    def pluck(self, column: str) -> List[Any]:
        return [
            (row.get_attribute(column) if self.model_class else row[column])
            for row in self.get()
        ]

    def exists(self) -> bool:
        return self.count() > 0

    def _aggregate(self, expression: str) -> Any:
        # GROUP BY is cleared too: an aggregate over a grouped query would
        # otherwise return only the first group's value.
        original = (self._columns, self._orders, self._group_by)
        self._columns, self._orders, self._group_by = [f"{expression} AS aggregate"], [], []
        try:
            query, params = self.to_sql()
            row = self.db.statement(query, params, read=True).fetchone()
        finally:
            self._columns, self._orders, self._group_by = original
        return row["aggregate"] if row is not None else None

    def count(self, column: str = "*") -> int:
        """Number of matching rows (not groups — grouping is ignored here)."""
        return int(self._aggregate(f"COUNT({column})") or 0)

    def sum(self, column: str) -> Any:
        return self._aggregate(f"SUM({column})") or 0

    def avg(self, column: str) -> Any:
        return self._aggregate(f"AVG({column})")

    def max(self, column: str) -> Any:
        return self._aggregate(f"MAX({column})")

    def min(self, column: str) -> Any:
        return self._aggregate(f"MIN({column})")

    #: Hard ceiling on `per_page` — an uncapped value lets a single client
    #: request an arbitrarily large page and load the database.
    MAX_PER_PAGE = 100

    def paginate(self, per_page: int = 15, page: int = 1) -> Any:
        total = self.count()
        page = max(page, 1)
        per_page = max(1, min(int(per_page or 15), self.MAX_PER_PAGE))
        self._limit = per_page
        self._offset = (page - 1) * per_page
        items = self.get()
        items.pagination = {
            "total": total,
            "per_page": per_page,
            "current_page": page,
            "last_page": max(1, -(-total // per_page)),
        }
        return items

    # -- writes ----------------------------------------------------------------

    def insert(self, values: Dict[str, Any]) -> Any:
        return self.db.insert_get_id(self.table_name, values)

    def update(self, values: Dict[str, Any]) -> int:
        if not values:
            return 0
        values = dict(values)
        # Only model-backed updates get an updated_at stamp — raw table updates
        # (pivot tables, ad-hoc tables) may not have the column at all.
        if self.model_class is not None and getattr(self.model_class, "timestamps", True):
            values.setdefault("updated_at", datetime.now(timezone.utc).replace(tzinfo=None).isoformat())
        for column in values:
            _assert_identifier(column)
        assignments = ", ".join(f"{column} = ?" for column in values)
        params = list(values.values())

        where_sql, where_params = self._compile_wheres()
        query = f"UPDATE {self.table_name} SET {assignments}{where_sql}"
        return self.db.statement(query, params + where_params).rowcount

    def delete(self) -> int:
        where_sql, params = self._compile_wheres()
        result = self.db.statement(f"DELETE FROM {self.table_name}{where_sql}", params)
        return result.rowcount if result.rowcount and result.rowcount > 0 else 0

    def truncate(self) -> None:
        driver = getattr(self.db, "driver", "sqlite")
        if driver == "sqlite":
            self.db.statement(f"DELETE FROM {self.table_name}")
        else:
            self.db.statement(f"TRUNCATE TABLE {self.table_name}")
