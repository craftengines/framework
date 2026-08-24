"""
QueryBuilder — Fluent, chainable SQL query builder for Craft ORM.
Category: Core Framework (ORM).
Relations:
  - Built by `Model.query()` (`engine/orm/model.py`); powers relationship
    proxies (`engine/orm/relationships.py`).
  - Executes through `engine/orm/connection.py` via the `DatabaseManager`
    (`engine/orm/db.py`), never SQLAlchemy.
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

from engine.orm.postgres.macros import PostgresMacros

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


class QueryBuilder(PostgresMacros):
    """Fluent SQL query builder backed by the application's DatabaseManager.

    The PostgreSQL macros (`where_json_contains`, `where_search`,
    `order_by_vector_distance`, …) arrive through `PostgresMacros`. They build
    an `Expr` rather than widening the allowlists below, so the identifier and
    operator checks that guard every clause here stay exactly as strict.
    """

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
            from engine.container.application import Container

            # No silent fallback to a default `DatabaseManager()`: that builds a
            # *different* connection from the application's, so a container
            # failure turned into queries quietly running against the wrong
            # database — reads that return nothing and writes that land
            # somewhere nobody looks. A stack trace is the kinder outcome.
            self.db = Container.getInstance().make("db")

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
        self._vector_searches: List[Dict[str, Any]] = []
        self._vector_orders: List[Dict[str, Any]] = []
        self._vector_metric: str = "cosine"
        #: Framework-authored fragments (`engine/orm/expression.py`) projected
        #: or ordered by. Kept apart from `_columns` / `_orders` because they
        #: carry bindings, and bindings must be spliced in clause order.
        self._select_exprs: List[tuple] = []
        self._order_exprs: List[tuple] = []

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

    # -- expression clauses ----------------------------------------------------

    def where_expr(self, expr: Any, boolean: str = "AND") -> "QueryBuilder":
        """Constrain by a framework-authored fragment.

        Not application API — the dialect macros in `engine/orm/postgres/` are.
        `Expr` exists so those macros can reach operators the allowlists above
        deliberately refuse (`@>`, `@@`, `<=>`) *without* opening the same door
        to a column name that came from request input: the operator is a
        literal in framework source, every value is a binding.
        """
        from engine.orm.expression import Expr

        if not isinstance(expr, Expr):
            raise TypeError(
                "where_expr() takes an Expr built by a framework macro, not a "
                "SQL string. Building one from caller input would bypass every "
                "identifier check in this module."
            )
        self._wheres.append({"boolean": boolean, "type": "expr", "expr": expr})
        return self

    def or_where_expr(self, expr: Any) -> "QueryBuilder":
        return self.where_expr(expr, boolean="OR")

    def select_expr(self, expr: Any, alias: str) -> "QueryBuilder":
        """Project a fragment under `alias`, alongside the existing columns.

        A bare `SELECT *` is widened to `table.*` first, so adding a computed
        column (a search rank, a vector distance) never costs the row itself.
        """
        from engine.orm.expression import Expr

        if not isinstance(expr, Expr):
            raise TypeError("select_expr() takes an Expr built by a framework macro.")
        _assert_identifier(alias)
        if self._columns == ["*"]:
            self._columns = [f"{self.table_name}.*"]
        self._select_exprs.append((expr, alias))
        return self

    def order_by_expr(self, expr: Any, direction: str = "asc") -> "QueryBuilder":
        from engine.orm.expression import Expr

        if not isinstance(expr, Expr):
            raise TypeError("order_by_expr() takes an Expr built by a framework macro.")
        self._order_exprs.append(
            (expr, "DESC" if str(direction).lower() == "desc" else "ASC")
        )
        return self

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

    def order_by_vector_similarity(
        self,
        column: str,
        vector: Sequence[float],
        ascending: bool = False,
    ) -> "QueryBuilder":
        """Sort by vector similarity — most similar first.

        On PostgreSQL this compiles to pgvector's distance operator, which an
        HNSW index can answer directly. Elsewhere it falls back to scoring in
        Python, which reads the whole result set into the process; that path
        exists so the test-suite and development on SQLite keep working, not
        because it is a way to search a real corpus.

        `ascending=True` means least similar first. It reads backwards next to
        the distance operator — where ascending distance *is* descending
        similarity — so the flag is kept on the similarity reading it has always
        had, and the operator ordering is derived from it.
        """
        _assert_identifier(column)
        if self._vector_native():
            expression = self._vector_distance(column, vector, self._vector_metric)
            self.select_expr(expression, "distance")
            # Ascending distance is descending similarity, so the flag inverts.
            return self.order_by_expr(expression, "desc" if ascending else "asc")

        self._vector_orders.append({
            "column": column,
            "vector": list(vector),
            "ascending": ascending,
        })
        return self

    def where_vector_similar(
        self,
        column: str,
        vector: Sequence[float],
        min_similarity: float = 0.7,
        metric: str = "cosine",
    ) -> "QueryBuilder":
        """Keep only rows at least `min_similarity` close to `vector`."""
        _assert_identifier(column)
        self._vector_metric = str(metric).lower()
        if self._vector_native():
            return self.where_vector_near(
                column, vector, min_similarity=min_similarity, metric=self._vector_metric
            )

        self._vector_searches.append({
            "column": column,
            "vector": list(vector),
            "min_similarity": float(min_similarity),
            "metric": self._vector_metric,
        })
        return self

    def _vector_native(self) -> bool:
        """Whether the database can do the distance arithmetic itself."""
        dialect = getattr(self.db, "dialect", None)
        return dialect is not None and dialect.supports("vector")

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
            # Absent for an "expr" clause, which carries its own SQL.
            column = where.get("column")

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
            elif kind == "expr":
                condition = where["expr"].sql
                params.extend(where["expr"].bindings)
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

    def to_sql(self, without_paging: bool = False) -> tuple[str, List[Any]]:
        """Compile to SQL and its bindings.

        `without_paging` omits LIMIT/OFFSET, for the one caller that has to
        score rows in Python before it can know which page they belong to.
        """
        # Bindings are accumulated strictly in clause order. It matters because
        # `normalize_placeholders()` (connection.py) rewrites `?` positionally
        # for the format-paramstyle drivers — a select expression's value
        # appended after the wheres would be bound to a where's placeholder.
        params: List[Any] = []

        projections = list(self._columns)
        for expr, alias in self._select_exprs:
            projections.append(f"{expr.sql} AS {alias}")
            params.extend(expr.bindings)

        distinct = "DISTINCT " if self._distinct else ""
        query = f"SELECT {distinct}{', '.join(projections)} FROM {self.table_name}"

        for join in self._joins:
            query += f" {join}"

        where_sql, where_params = self._compile_wheres()
        query += where_sql
        params.extend(where_params)

        if self._group_by:
            query += " GROUP BY " + ", ".join(self._group_by)

        if self._having:
            parts = []
            for having in self._having:
                parts.append(f"{having['column']} {having['operator']} ?")
                params.append(having["value"])
            query += " HAVING " + " AND ".join(parts)

        orders = list(self._orders)
        for expr, direction in self._order_exprs:
            orders.append(f"{expr.sql} {direction}")
            params.extend(expr.bindings)
        if orders:
            query += " ORDER BY " + ", ".join(orders)

        if not without_paging:
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
                from engine.orm.exceptions import RelationNotFoundError

                raise RelationNotFoundError(
                    f"{self.model_class.__name__} has no relation [{name}]."
                )

            relation = method(models[0])
            keys = relation.eager_keys(models)
            results = relation.eager_query(keys) if keys else []
            relation.match(models, results)

    def get(self) -> Any:
        needs_scoring = bool(self._vector_searches or self._vector_orders)

        query, params = self.to_sql(without_paging=needs_scoring)
        rows = self.db.statement(query, params, read=True).fetchall()

        results: List[Any] = []
        for row in rows:
            row_dict = dict(row)
            results.append(self.model_class(row_dict) if self.model_class else row_dict)

        if needs_scoring:
            results = self._score_vectors(results)

        self._eager_load(results)

        from engine.support.collection import Collection

        return Collection(results)

    # -- in-process vector scoring (drivers without pgvector) ------------------

    def _score_vectors(self, results: List[Any]) -> List[Any]:
        """Filter and rank by cosine similarity in Python.

        Only reached on a driver without pgvector — everywhere else the
        distance operator does this inside the database, against an index.
        Kept so development and the test-suite work on SQLite.

        Two things it gets right that the previous implementation did not: the
        SQL runs *without* LIMIT/OFFSET so scoring sees the whole candidate set
        (paging applied before scoring silently truncated the corpus, then
        ranked whatever survived), and paging is re-applied afterwards so the
        page returned matches the page requested.
        """
        scored: List[Any] = []
        for item in results:
            score = None
            keep = True

            for search in self._vector_searches:
                similarity = self._cosine(item, search["column"], search["vector"])
                if similarity is None or similarity < search["min_similarity"]:
                    keep = False
                    break
                score = similarity

            if not keep:
                continue

            for order in self._vector_orders:
                similarity = self._cosine(item, order["column"], order["vector"])
                if similarity is not None:
                    score = similarity

            self._set_score(item, 0.0 if score is None else score)
            scored.append(item)

        if self._vector_orders:
            ascending = self._vector_orders[0]["ascending"]
            scored.sort(key=self._read_score, reverse=not ascending)

        offset = self._offset or 0
        if self._limit is not None:
            return scored[offset:offset + self._limit]
        return scored[offset:] if offset else scored

    @staticmethod
    def _row_vector(item: Any, column: str) -> Optional[List[float]]:
        raw = (
            item.get_attribute(column) if hasattr(item, "get_attribute") else item.get(column)
        )
        from engine.orm.casts import VectorCast

        value = VectorCast().hydrate(raw, "sqlite")
        if isinstance(value, (list, tuple)):
            try:
                return [float(component) for component in value]
            except (TypeError, ValueError):
                return None
        return None

    @classmethod
    def _cosine(cls, item: Any, column: str, target: Sequence[float]) -> Optional[float]:
        vector = cls._row_vector(item, column)
        if vector is None or len(vector) != len(target):
            # A dimension mismatch is a data problem, not a distance of zero —
            # scoring it 0.0 would quietly rank it last instead of excluding it.
            return None
        # strict: the length check above is the only thing that makes this
        # meaningful, and a silent truncation would score a mismatched vector
        # as a partial match rather than excluding it.
        dot = sum(a * b for a, b in zip(vector, target, strict=True))
        norm_a = sum(a * a for a in vector) ** 0.5
        norm_b = sum(b * b for b in target) ** 0.5
        return (dot / (norm_a * norm_b)) if norm_a > 0 and norm_b > 0 else 0.0

    @staticmethod
    def _set_score(item: Any, score: float) -> None:
        if isinstance(item, dict):
            item["similarity_score"] = score
        else:
            item.similarity_score = score

    @staticmethod
    def _read_score(item: Any) -> float:
        if isinstance(item, dict):
            return float(item.get("similarity_score") or 0.0)
        return float(getattr(item, "similarity_score", 0.0) or 0.0)

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
        # otherwise return only the first group's value. So are the expression
        # projections and orderings — a `COUNT(*)` that still carried a vector
        # distance in its SELECT list would bind values the aggregate has no
        # placeholder for, and ordering an aggregate is meaningless anyway.
        original = (
            self._columns, self._orders, self._group_by,
            self._select_exprs, self._order_exprs,
        )
        self._columns = [f"{expression} AS aggregate"]
        self._orders, self._group_by = [], []
        self._select_exprs, self._order_exprs = [], []
        try:
            query, params = self.to_sql()
            row = self.db.statement(query, params, read=True).fetchone()
        finally:
            (
                self._columns, self._orders, self._group_by,
                self._select_exprs, self._order_exprs,
            ) = original
        return row["aggregate"] if row is not None else None

    @staticmethod
    def _aggregate_column(column: str) -> str:
        """Validate a column used inside an aggregate.

        Aggregates interpolate the column straight into SQL, so they need the
        same identifier allowlist every other clause in this file applies —
        they were the one hole in it, and `count(request.input("col"))` is an
        ordinary-looking way to reach it.
        """
        return "*" if column == "*" else _assert_identifier(column)

    def count(self, column: str = "*") -> int:
        """Number of matching rows (not groups — grouping is ignored here)."""
        return int(self._aggregate(f"COUNT({self._aggregate_column(column)})") or 0)

    def sum(self, column: str) -> Any:
        return self._aggregate(f"SUM({self._aggregate_column(column)})") or 0

    def avg(self, column: str) -> Any:
        return self._aggregate(f"AVG({self._aggregate_column(column)})")

    def max(self, column: str) -> Any:
        return self._aggregate(f"MAX({self._aggregate_column(column)})")

    def min(self, column: str) -> Any:
        return self._aggregate(f"MIN({self._aggregate_column(column)})")

    #: Hard ceiling on `per_page` — an uncapped value lets a single client
    #: request an arbitrarily large page and load the database.
    MAX_PER_PAGE = 100

    def paginate(self, per_page: int = 15, page: int = 1) -> Any:
        if self._vector_searches and not self._vector_native():
            # A SQL COUNT cannot see a filter applied in Python, so the totals
            # used to describe a different result set than the one returned —
            # "1 of 40" over three items. Count what the caller will actually
            # get instead.
            return self._paginate_scored(per_page, page)

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

    def _paginate_scored(self, per_page: int, page: int) -> Any:
        """Paginate a result set whose filter runs in Python, honestly."""
        page = max(page, 1)
        per_page = max(1, min(int(per_page or 15), self.MAX_PER_PAGE))

        limit, offset = self._limit, self._offset
        self._limit = self._offset = None
        try:
            everything = list(self.get())
        finally:
            self._limit, self._offset = limit, offset

        total = len(everything)
        start = (page - 1) * per_page

        from engine.support.collection import Collection

        items = Collection(everything[start:start + per_page])
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
