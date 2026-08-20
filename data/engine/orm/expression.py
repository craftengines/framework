"""Bound SQL fragments for the Craft query builder.

An `Expr` is SQL the *framework* wrote, paired with the bindings that carry
every value a caller supplied. It is the one sanctioned way past the identifier
and operator allowlists in `engine/orm/query_builder.py`, and it is deliberately
narrow: framework macros build it, application code does not.

Category: Core Framework (ORM).
Relations:
  - Consumed by `QueryBuilder.where_expr()` / `select_expr()` / `order_by_expr()`
    (`engine/orm/query_builder.py`).
  - Produced by the PostgreSQL macros in `engine/orm/postgres/`.
References:
  - Guide: `documentation/orm.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from typing import Any, List, Sequence


class Expr:
    """A SQL fragment with `?` placeholders and the values that fill them.

    The invariant that makes this safe: `sql` is a literal written *inside the
    framework*, and every value that came from outside it lives in `bindings`.
    A macro that interpolates a caller's string into `sql` has broken the
    invariant — run identifiers through `_assert_identifier` and pass
    everything else as a binding.

    The placeholder style is the framework's own `?`, normalised per driver by
    `normalize_placeholders()` (`engine/orm/connection.py`), so a fragment
    written once works on all three drivers.
    """

    __slots__ = ("sql", "bindings")

    def __init__(self, sql: str, bindings: Sequence[Any] = ()) -> None:
        if not isinstance(sql, str) or not sql.strip():
            raise ValueError("An Expr needs a non-empty SQL fragment.")
        placeholders = sql.count("?")
        bindings = list(bindings)
        if placeholders != len(bindings):
            # Catches the mistake at construction rather than as a driver error
            # thousands of lines away: psycopg2 reports "not all arguments
            # converted", which says nothing about which macro built the clause.
            raise ValueError(
                f"Expr has {placeholders} placeholder(s) but {len(bindings)} "
                f"binding(s): {sql!r}"
            )
        self.sql = sql
        self.bindings: List[Any] = bindings

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Expr({self.sql!r}, {self.bindings!r})"

    def __eq__(self, other: Any) -> bool:
        return (
            isinstance(other, Expr)
            and other.sql == self.sql
            and other.bindings == self.bindings
        )


class Raw:
    """A literal SQL snippet used where a *value* is expected in DDL.

    Column defaults are compiled by `Grammar.format_default`, which quotes
    whatever it is given — correct for `"pending"`, wrong for
    `gen_random_uuid()`. Wrapping the snippet says "emit this verbatim", and
    the type makes that decision visible at the call site instead of hiding it
    behind a string that happens to contain brackets.

    DDL only, and only from migration or framework source: it carries no
    bindings, so nothing from a request may ever reach it.
    """

    __slots__ = ("sql",)

    def __init__(self, sql: str) -> None:
        if not isinstance(sql, str) or not sql.strip():
            raise ValueError("Raw() needs a non-empty SQL snippet.")
        self.sql = sql

    def __str__(self) -> str:
        return self.sql

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Raw({self.sql!r})"

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Raw) and other.sql == self.sql


__all__ = ["Expr", "Raw"]
