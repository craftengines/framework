"""PostgreSQL query macros for the Craft query builder.

The builder's identifier and operator allowlists exist because column names
reach SQL by interpolation. Loosening them to admit `@>`, `@@` or `<=>` would
hand that same door to `request.input()`. These macros instead build an `Expr`
(`engine/orm/expression.py`): the operator is a literal written here, the
identifier goes through the same `_assert_identifier` every other clause uses,
and every caller-supplied value is a binding.

That is the whole design. Adding a macro means adding a method here, never
relaxing a check there.

Category: Core Framework (ORM).
Relations:
  - Mixed into `QueryBuilder` (`engine/orm/query_builder.py`).
  - Index helpers that make these fast live in `engine/migrations/schema.py`.
References:
  - Guide: `documentation/orm.md#postgresql-query-macros`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import json
from typing import Any, Sequence

from engine.orm.casts import vector_literal
from engine.orm.expression import Expr

#: Text search configurations the framework will name in SQL. A `regconfig`
#: cannot be bound, so it is interpolated — and therefore has to come from a
#: fixed set rather than from a caller.
LANGUAGES = frozenset({
    "simple", "english", "portuguese", "spanish", "french", "german",
    "italian", "dutch", "russian", "swedish", "norwegian", "danish",
    "finnish", "hungarian", "romanian", "turkish",
})

#: How a search string becomes a `tsquery`.
QUERY_FUNCTIONS = {
    # The default on purpose: `websearch_to_tsquery` accepts what a person
    # actually types — quoted phrases, OR, a leading minus — and never raises
    # on input the others reject. A search box must not return a 500 because
    # somebody typed an unbalanced quote.
    "websearch": "websearch_to_tsquery",
    "plain": "plainto_tsquery",
    "phrase": "phraseto_tsquery",
    "raw": "to_tsquery",
}

#: Distance operators. Cosine leads because the embeddings the AI drivers
#: produce are normalised, where cosine and inner product agree and cosine is
#: the one whose numbers a reader can interpret.
VECTOR_OPERATORS = {"cosine": "<=>", "l2": "<->", "inner_product": "<#>"}

#: Comparison operators a macro may place next to a JSON extraction. The same
#: allowlist the rest of the builder uses, restated here so this module does
#: not import it at module scope and create a cycle.
COMPARISONS = {"=", "!=", "<>", "<", "<=", ">", ">=", "LIKE", "NOT LIKE"}


def _column(name: str) -> str:
    from engine.orm.query_builder import _assert_identifier

    return _assert_identifier(name)


def _language(language: str) -> str:
    if language not in LANGUAGES:
        raise ValueError(
            f"Unknown text search language [{language}]. Known: "
            f"{', '.join(sorted(LANGUAGES))}."
        )
    return language


class PostgresMacros:
    """Query macros for PostgreSQL types, mixed into the builder.

    Each one checks the capability it needs before building anything, so a
    query written against PostgreSQL fails on SQLite with a message naming the
    driver and the feature rather than a syntax error from the driver.
    """

    def _require(self, feature: str, because: str) -> None:
        dialect = getattr(self.db, "dialect", None)
        if dialect is not None:
            dialect.require(feature, because)

    # -- JSONB -----------------------------------------------------------------

    def where_json_contains(self, column: str, value: Any) -> "PostgresMacros":
        """`meta @> '{"plan":"pro"}'` — the GIN-indexable containment test.

            Account.query().where_json_contains("meta", {"plan": "pro"})

        This is the one JSONB predicate a `jsonb_path_ops` index can serve, so
        it is the one to reach for when the filter is "does this document
        include that fragment".
        """
        self._require("jsonb", "backs where_json_contains()")
        return self.where_expr(
            Expr(f"{_column(column)} @> ?::jsonb", [json.dumps(value, default=str)])
        )

    def where_json_contained_by(self, column: str, value: Any) -> "PostgresMacros":
        """`meta <@ '{…}'` — the whole document fits inside `value`."""
        self._require("jsonb", "backs where_json_contained_by()")
        return self.where_expr(
            Expr(f"{_column(column)} <@ ?::jsonb", [json.dumps(value, default=str)])
        )

    def where_json_has_key(self, column: str, key: str) -> "PostgresMacros":
        """`meta ? 'plan'` — the key exists at the top level.

        Sent as `jsonb_exists(meta, ?)` rather than the `?` operator, which
        every driver placeholder style collides with.
        """
        self._require("jsonb", "backs where_json_has_key()")
        return self.where_expr(Expr(f"jsonb_exists({_column(column)}, ?)", [key]))

    def where_json_key(
        self, column: str, path: str, operator: str, value: Any
    ) -> "PostgresMacros":
        """`meta #>> '{usage,seats}' > '10'` — compare one extracted value.

        The path is bound as a text array, never interpolated, so a key taken
        from request input cannot reach the SQL text. Extraction yields text,
        so the comparison is textual: for numbers, reach for
        `where_json_path()` instead, where the operators are typed.
        """
        self._require("jsonb", "backs where_json_key()")
        if str(operator).upper() not in COMPARISONS:
            raise ValueError(f"Invalid SQL operator [{operator}].")
        keys = [part for part in str(path).split(".") if part]
        if not keys:
            raise ValueError("where_json_key() needs a non-empty path.")
        return self.where_expr(
            Expr(f"{_column(column)} #>> ? {operator} ?", [keys, value])
        )

    def where_json_path(self, column: str, jsonpath: str) -> "PostgresMacros":
        """SQL/JSON path predicate — one bound argument, typed comparisons.

            Order.query().where_json_path("lines", '$[*] ? (@.qty > 100)')
        """
        self._require("jsonb", "backs where_json_path()")
        return self.where_expr(
            Expr(f"jsonb_path_exists({_column(column)}, ?::jsonpath)", [jsonpath])
        )

    def order_by_json(
        self, column: str, path: str, direction: str = "asc"
    ) -> "PostgresMacros":
        self._require("jsonb", "backs order_by_json()")
        keys = [part for part in str(path).split(".") if part]
        return self.order_by_expr(
            Expr(f"{_column(column)} #>> ?", [keys]), direction
        )

    # -- arrays ----------------------------------------------------------------

    def where_array_contains(self, column: str, values: Sequence[Any]) -> "PostgresMacros":
        """`tags @> ARRAY[…]` — the row has *all* of them."""
        self._require("arrays", "backs where_array_contains()")
        return self.where_expr(Expr(f"{_column(column)} @> ?", [list(values)]))

    def where_array_overlaps(self, column: str, values: Sequence[Any]) -> "PostgresMacros":
        """`tags && ARRAY[…]` — the row has *any* of them. GIN-indexable."""
        self._require("arrays", "backs where_array_overlaps()")
        return self.where_expr(Expr(f"{_column(column)} && ?", [list(values)]))

    def where_array_has(self, column: str, value: Any) -> "PostgresMacros":
        """`? = ANY(tags)` — one element is present."""
        self._require("arrays", "backs where_array_has()")
        return self.where_expr(Expr(f"? = ANY({_column(column)})", [value]))

    def where_array_length(self, column: str, operator: str, length: int) -> "PostgresMacros":
        self._require("arrays", "backs where_array_length()")
        if str(operator).upper() not in COMPARISONS:
            raise ValueError(f"Invalid SQL operator [{operator}].")
        return self.where_expr(
            Expr(
                f"coalesce(array_length({_column(column)}, 1), 0) {operator} ?",
                [int(length)],
            )
        )

    # -- ranges ----------------------------------------------------------------

    def where_range_contains(
        self, column: str, value: Any, kind: str = "tsrange"
    ) -> "PostgresMacros":
        """`period @> '2026-08-20 14:00'::timestamp` — the point falls inside."""
        self._require("ranges", "backs where_range_contains()")
        from engine.orm.casts import RangeCast

        element = RangeCast(kind).KINDS[kind]
        return self.where_expr(Expr(f"{_column(column)} @> ?::{element}", [value]))

    def where_range_overlaps(
        self, column: str, lower: Any, upper: Any, kind: str = "tsrange"
    ) -> "PostgresMacros":
        """`period && tsrange(?, ?, '[)')` — the double-booking test.

        Half-open bounds, so a booking ending at 14:00 and one starting at
        14:00 do not overlap. The database enforces the same rule through an
        exclusion constraint; this is how you *ask* about it.
        """
        self._require("ranges", "backs where_range_overlaps()")
        from engine.orm.casts import RangeCast

        RangeCast(kind)  # validates the range type name
        return self.where_expr(
            Expr(f"{_column(column)} && {kind}(?, ?, '[)')", [lower, upper])
        )

    def where_range_adjacent(
        self, column: str, lower: Any, upper: Any, kind: str = "tsrange"
    ) -> "PostgresMacros":
        """`period -|- …` — the ranges touch without overlapping."""
        self._require("ranges", "backs where_range_adjacent()")
        from engine.orm.casts import RangeCast

        RangeCast(kind)
        return self.where_expr(
            Expr(f"{_column(column)} -|- {kind}(?, ?, '[)')", [lower, upper])
        )

    # -- full-text search ------------------------------------------------------

    def where_search(
        self,
        column: str,
        terms: str,
        *,
        language: str = "english",
        mode: str = "websearch",
    ) -> "PostgresMacros":
        """`search_document @@ websearch_to_tsquery('english', ?)`.

        Point it at a stored generated `tsvector` column — see
        `Blueprint.tsvector().generated_from()`. Building the vector in the
        WHERE clause instead recomputes it for every candidate row and forfeits
        the index entirely.
        """
        self._require("fulltext", "backs where_search()")
        function = QUERY_FUNCTIONS.get(mode)
        if function is None:
            raise ValueError(
                f"Unknown search mode [{mode}]. Known: "
                f"{', '.join(sorted(QUERY_FUNCTIONS))}."
            )
        return self.where_expr(
            Expr(f"{_column(column)} @@ {function}('{_language(language)}', ?)", [terms])
        )

    def order_by_relevance(
        self,
        column: str,
        terms: str,
        *,
        language: str = "english",
        mode: str = "websearch",
        alias: str = "relevance",
    ) -> "PostgresMacros":
        """Rank by `ts_rank_cd`, and project the score under `alias`.

        Cover density rather than plain `ts_rank`: it rewards terms appearing
        near each other, so a document containing the phrase outranks one that
        mentions both words on different pages. Plain `ts_rank` scores those
        the same.
        """
        self._require("fulltext", "backs order_by_relevance()")
        function = QUERY_FUNCTIONS[mode]
        expression = f"ts_rank_cd({_column(column)}, {function}('{_language(language)}', ?))"
        self.select_expr(Expr(expression, [terms]), alias)
        return self.order_by_expr(Expr(expression, [terms]), "desc")

    # -- trigram ---------------------------------------------------------------

    def where_similar(self, column: str, term: str, threshold: float = 0.3) -> "PostgresMacros":
        """Fuzzy match on trigram similarity.

        `similarity(col, ?) > ?` rather than the `%` operator: `%` reads its
        cutoff from `pg_trgm.similarity_threshold`, a session setting the
        connection pool would then have to manage. An explicit threshold is the
        same test with the value where the caller can see it.
        """
        self._require("trigram", "backs where_similar()")
        return self.where_expr(
            Expr(f"similarity({_column(column)}, ?) > ?", [term, float(threshold)])
        )

    def order_by_distance(self, column: str, term: str) -> "PostgresMacros":
        """`col <-> ?` — trigram distance, ascending.

        With a GiST trigram index this is an index scan, not a sort over the
        whole table.
        """
        self._require("trigram", "backs order_by_distance()")
        return self.order_by_expr(Expr(f"{_column(column)} <-> ?", [term]), "asc")

    # -- vectors ---------------------------------------------------------------

    @staticmethod
    def _vector_distance(column: str, vector: Sequence[float], metric: str = "cosine") -> Expr:
        """`column <=> '[…]'::vector` — built once, used by filter and order."""
        return Expr(
            f"{_column(column)} {_vector_operator(metric)} ?::vector",
            [vector_literal(vector)],
        )

    def where_vector_near(
        self,
        column: str,
        vector: Sequence[float],
        min_similarity: float = 0.7,
        metric: str = "cosine",
    ) -> "PostgresMacros":
        """Cosine similarity floor, as the distance ceiling the index understands.

        similarity = 1 - distance, so a 0.7 floor is a 0.3 ceiling. Expressed
        against the operator rather than computed in Python, which is what lets
        an HNSW index answer it.
        """
        self._require("vector", "backs vector search")
        distance = self._vector_distance(column, vector, metric)
        return self.where_expr(
            Expr(
                f"({distance.sql}) < ?",
                [*distance.bindings, 1.0 - float(min_similarity)],
            )
        )

    def order_by_vector_distance(
        self,
        column: str,
        vector: Sequence[float],
        metric: str = "cosine",
        alias: str = "distance",
    ) -> "PostgresMacros":
        """Nearest neighbours first, with the distance projected under `alias`."""
        self._require("vector", "backs vector search")
        expression = self._vector_distance(column, vector, metric)
        self.select_expr(expression, alias)
        return self.order_by_expr(expression, "asc")


def _vector_operator(metric: str) -> str:
    operator = VECTOR_OPERATORS.get(str(metric).lower())
    if operator is None:
        raise ValueError(
            f"Unknown vector metric [{metric}]. Known: "
            f"{', '.join(sorted(VECTOR_OPERATORS))}."
        )
    return operator


__all__ = ["LANGUAGES", "QUERY_FUNCTIONS", "VECTOR_OPERATORS", "PostgresMacros"]
