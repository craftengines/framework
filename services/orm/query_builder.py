"""QueryBuilder for Craft ORM."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import inspect
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Type


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
        self._columns = list(columns) or ["*"]
        return self

    def distinct(self) -> "QueryBuilder":
        self._distinct = True
        return self

    # -- where clauses ---------------------------------------------------------

    def where(self, column: str, operator_or_value: Any, value: Any = None) -> "QueryBuilder":
        if value is None and not isinstance(operator_or_value, str):
            op, val = "=", operator_or_value
        elif value is None:
            op, val = "=", operator_or_value
        else:
            op, val = operator_or_value, value
        self._wheres.append({"boolean": "AND", "column": column, "operator": op, "value": val})
        return self

    def or_where(self, column: str, operator_or_value: Any, value: Any = None) -> "QueryBuilder":
        self.where(column, operator_or_value, value)
        self._wheres[-1]["boolean"] = "OR"
        return self

    def where_in(self, column: str, values: Sequence[Any]) -> "QueryBuilder":
        self._wheres.append({"boolean": "AND", "column": column, "type": "in", "value": list(values)})
        return self

    def where_not_in(self, column: str, values: Sequence[Any]) -> "QueryBuilder":
        self._wheres.append({"boolean": "AND", "column": column, "type": "not_in", "value": list(values)})
        return self

    def where_null(self, column: str) -> "QueryBuilder":
        self._wheres.append({"boolean": "AND", "column": column, "type": "null"})
        return self

    def where_not_null(self, column: str) -> "QueryBuilder":
        self._wheres.append({"boolean": "AND", "column": column, "type": "not_null"})
        return self

    def where_between(self, column: str, low: Any, high: Any) -> "QueryBuilder":
        self._wheres.append({"boolean": "AND", "column": column, "type": "between", "value": [low, high]})
        return self

    def where_like(self, column: str, pattern: str) -> "QueryBuilder":
        return self.where(column, "LIKE", pattern)

    # -- joins / grouping ------------------------------------------------------

    def join(self, table: str, first: str, operator: str, second: str) -> "QueryBuilder":
        self._joins.append(f"INNER JOIN {table} ON {first} {operator} {second}")
        return self

    def left_join(self, table: str, first: str, operator: str, second: str) -> "QueryBuilder":
        self._joins.append(f"LEFT JOIN {table} ON {first} {operator} {second}")
        return self

    def group_by(self, *columns: str) -> "QueryBuilder":
        self._group_by.extend(columns)
        return self

    def having(self, column: str, operator: str, value: Any) -> "QueryBuilder":
        self._having.append({"column": column, "operator": operator, "value": value})
        return self

    # -- ordering / paging -----------------------------------------------------

    def order_by(self, column: str, direction: str = "asc") -> "QueryBuilder":
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

        clauses: List[str] = []
        params: List[Any] = []
        for index, where in enumerate(self._wheres):
            prefix = "" if index == 0 else f" {where.get('boolean', 'AND')} "
            kind = where.get("type")
            column = where["column"]

            if kind == "in" or kind == "not_in":
                if not where["value"]:
                    clauses.append(f"{prefix}1 = {'0' if kind == 'in' else '1'}")
                    continue
                placeholders = ", ".join(["?"] * len(where["value"]))
                keyword = "IN" if kind == "in" else "NOT IN"
                clauses.append(f"{prefix}{column} {keyword} ({placeholders})")
                params.extend(where["value"])
            elif kind == "null":
                clauses.append(f"{prefix}{column} IS NULL")
            elif kind == "not_null":
                clauses.append(f"{prefix}{column} IS NOT NULL")
            elif kind == "between":
                clauses.append(f"{prefix}{column} BETWEEN ? AND ?")
                params.extend(where["value"])
            else:
                clauses.append(f"{prefix}{column} {where['operator']} ?")
                params.append(where["value"])

        return " WHERE " + "".join(clauses), params

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
        self._limit = 1
        items = self.get()
        return items[0] if len(items) > 0 else None

    def find(self, id_val: Any) -> Any:
        return self.where("id", id_val).first()

    def pluck(self, column: str) -> List[Any]:
        return [
            (row.get_attribute(column) if self.model_class else row[column])
            for row in self.get()
        ]

    def exists(self) -> bool:
        return self.count() > 0

    def _aggregate(self, expression: str) -> Any:
        original_columns, original_orders = self._columns, self._orders
        self._columns, self._orders = [f"{expression} AS aggregate"], []
        try:
            query, params = self.to_sql()
            row = self.db.statement(query, params, read=True).fetchone()
        finally:
            self._columns, self._orders = original_columns, original_orders
        return row["aggregate"] if row is not None else None

    def count(self, column: str = "*") -> int:
        return int(self._aggregate(f"COUNT({column})") or 0)

    def sum(self, column: str) -> Any:
        return self._aggregate(f"SUM({column})") or 0

    def avg(self, column: str) -> Any:
        return self._aggregate(f"AVG({column})")

    def max(self, column: str) -> Any:
        return self._aggregate(f"MAX({column})")

    def min(self, column: str) -> Any:
        return self._aggregate(f"MIN({column})")

    def paginate(self, per_page: int = 15, page: int = 1) -> Any:
        total = self.count()
        self._limit = per_page
        self._offset = (max(page, 1) - 1) * per_page
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
        values.setdefault("updated_at", datetime.now(timezone.utc).replace(tzinfo=None).isoformat())
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
