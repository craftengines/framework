"""Validator for Craft Framework.

Rules are given per field as a list or a pipe-delimited string::

    Validator(data, {
        "name":     ["required", "string", "max:255"],
        "email":    "required|email|unique:users,email",
        "age":      ["nullable", "integer", "between:18,120"],
        "password": ["required", "min:8", "confirmed"],
    })
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional, Union

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
URL_RE = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE)
ALPHA_RE = re.compile(r"^[a-zA-Z]+$")
ALPHA_NUM_RE = re.compile(r"^[a-zA-Z0-9]+$")
ALPHA_DASH_RE = re.compile(r"^[a-zA-Z0-9_-]+$")
UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)

Rules = Dict[str, Union[str, List[Any]]]


class Validator:
    """Validates a data bag against a rule set."""

    def __init__(
        self,
        data: Dict[str, Any],
        rules: Rules,
        messages: Optional[Dict[str, str]] = None,
    ):
        self.data = data or {}
        self.rules = rules or {}
        self.messages = messages or {}
        self.errors: Dict[str, List[str]] = {}
        self._validate()

    # -- rule parsing ----------------------------------------------------------

    @staticmethod
    def _normalise(rule_list: Union[str, List[Any]]) -> List[str]:
        if isinstance(rule_list, str):
            return [r for r in rule_list.split("|") if r]
        return [r for r in rule_list if r]

    @staticmethod
    def _split(rule: str):
        name, _, argument = str(rule).partition(":")
        args = [a.strip() for a in argument.split(",")] if argument else []
        return name.strip().lower(), args

    # -- driving ---------------------------------------------------------------

    def _validate(self) -> None:
        for field, rule_list in self.rules.items():
            rules = self._normalise(rule_list)
            value = self.data.get(field)

            present = field in self.data and value not in (None, "")
            nullable = any(self._split(r)[0] == "nullable" for r in rules)

            for rule in rules:
                name, args = self._split(rule)

                if name in ("nullable", "sometimes"):
                    continue

                # Only `required*` rules run against an absent value; everything
                # else would report a spurious type error on an empty optional.
                if not present and not name.startswith("required"):
                    continue
                if not present and nullable:
                    continue

                handler: Optional[Callable] = getattr(self, f"_rule_{name}", None)
                if handler is None:
                    continue  # unknown rule — ignore rather than reject data
                handler(field, value, args)

    def _add_error(self, field: str, message: str) -> None:
        custom = self.messages.get(f"{field}.{message.split(' ')[0]}") or self.messages.get(field)
        self.errors.setdefault(field, []).append(custom or message)

    # -- presence --------------------------------------------------------------

    def _rule_required(self, field: str, value: Any, args: List[str]) -> None:
        if value is None or value == "" or value == [] or value == {}:
            self._add_error(field, f"{field} is required")

    def _rule_required_if(self, field: str, value: Any, args: List[str]) -> None:
        if len(args) >= 2 and str(self.data.get(args[0])) == args[1]:
            self._rule_required(field, value, [])

    def _rule_required_with(self, field: str, value: Any, args: List[str]) -> None:
        if any(self.data.get(other) not in (None, "") for other in args):
            self._rule_required(field, value, [])

    # -- types -----------------------------------------------------------------

    def _rule_string(self, field: str, value: Any, args: List[str]) -> None:
        if not isinstance(value, str):
            self._add_error(field, f"{field} must be a string")

    def _rule_integer(self, field: str, value: Any, args: List[str]) -> None:
        # bool is a subclass of int — accepting True as an integer is a bug.
        if isinstance(value, bool) or not isinstance(value, int):
            if not (isinstance(value, str) and value.lstrip("-").isdigit()):
                self._add_error(field, f"{field} must be an integer")

    def _rule_numeric(self, field: str, value: Any, args: List[str]) -> None:
        if isinstance(value, bool):
            self._add_error(field, f"{field} must be numeric")
            return
        if isinstance(value, (int, float)):
            return
        try:
            float(value)
        except (TypeError, ValueError):
            self._add_error(field, f"{field} must be numeric")

    def _rule_boolean(self, field: str, value: Any, args: List[str]) -> None:
        if value not in (True, False, 0, 1, "0", "1", "true", "false"):
            self._add_error(field, f"{field} must be a boolean")

    def _rule_array(self, field: str, value: Any, args: List[str]) -> None:
        if not isinstance(value, (list, tuple)):
            self._add_error(field, f"{field} must be an array")

    def _rule_date(self, field: str, value: Any, args: List[str]) -> None:
        from datetime import date, datetime

        if isinstance(value, (date, datetime)):
            return
        try:
            datetime.fromisoformat(str(value))
        except ValueError:
            self._add_error(field, f"{field} must be a valid date")

    # -- formats ---------------------------------------------------------------

    def _pattern(self, field: str, value: Any, pattern, message: str) -> None:
        if not isinstance(value, str) or not pattern.match(value):
            self._add_error(field, message)

    def _rule_email(self, field: str, value: Any, args: List[str]) -> None:
        self._pattern(field, value, EMAIL_RE, f"{field} must be a valid email address")

    def _rule_url(self, field: str, value: Any, args: List[str]) -> None:
        self._pattern(field, value, URL_RE, f"{field} must be a valid URL")

    def _rule_uuid(self, field: str, value: Any, args: List[str]) -> None:
        self._pattern(field, value, UUID_RE, f"{field} must be a valid UUID")

    def _rule_alpha(self, field: str, value: Any, args: List[str]) -> None:
        self._pattern(field, value, ALPHA_RE, f"{field} must contain only letters")

    def _rule_alpha_num(self, field: str, value: Any, args: List[str]) -> None:
        self._pattern(field, value, ALPHA_NUM_RE, f"{field} must be alphanumeric")

    def _rule_alpha_dash(self, field: str, value: Any, args: List[str]) -> None:
        self._pattern(
            field, value, ALPHA_DASH_RE,
            f"{field} may contain only letters, numbers, dashes and underscores",
        )

    def _rule_regex(self, field: str, value: Any, args: List[str]) -> None:
        if not args:
            return
        if not isinstance(value, str) or not re.search(args[0], value):
            self._add_error(field, f"{field} format is invalid")

    # -- size ------------------------------------------------------------------

    @staticmethod
    def _size_of(value: Any) -> float:
        if isinstance(value, bool):
            return 0
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, (str, list, tuple, dict)):
            return len(value)
        return 0

    def _rule_min(self, field: str, value: Any, args: List[str]) -> None:
        if args and self._size_of(value) < float(args[0]):
            self._add_error(field, f"{field} must be at least {args[0]}")

    def _rule_max(self, field: str, value: Any, args: List[str]) -> None:
        if args and self._size_of(value) > float(args[0]):
            self._add_error(field, f"{field} may not be greater than {args[0]}")

    def _rule_between(self, field: str, value: Any, args: List[str]) -> None:
        if len(args) >= 2:
            size = self._size_of(value)
            if size < float(args[0]) or size > float(args[1]):
                self._add_error(field, f"{field} must be between {args[0]} and {args[1]}")

    def _rule_size(self, field: str, value: Any, args: List[str]) -> None:
        if args and self._size_of(value) != float(args[0]):
            self._add_error(field, f"{field} must be {args[0]}")

    # -- sets and comparisons --------------------------------------------------

    def _rule_in(self, field: str, value: Any, args: List[str]) -> None:
        if str(value) not in args:
            self._add_error(field, f"{field} must be one of: {', '.join(args)}")

    def _rule_not_in(self, field: str, value: Any, args: List[str]) -> None:
        if str(value) in args:
            self._add_error(field, f"{field} must not be one of: {', '.join(args)}")

    def _rule_same(self, field: str, value: Any, args: List[str]) -> None:
        if args and value != self.data.get(args[0]):
            self._add_error(field, f"{field} must match {args[0]}")

    def _rule_different(self, field: str, value: Any, args: List[str]) -> None:
        if args and value == self.data.get(args[0]):
            self._add_error(field, f"{field} must be different from {args[0]}")

    def _rule_confirmed(self, field: str, value: Any, args: List[str]) -> None:
        if value != self.data.get(f"{field}_confirmation"):
            self._add_error(field, f"{field} confirmation does not match")

    def _rule_accepted(self, field: str, value: Any, args: List[str]) -> None:
        if value not in (True, 1, "1", "on", "yes", "true"):
            self._add_error(field, f"{field} must be accepted")

    # -- database --------------------------------------------------------------

    def _db(self) -> Any:
        from services.container.application import Container

        return Container.getInstance().make("db")

    def _rule_unique(self, field: str, value: Any, args: List[str]) -> None:
        """unique:table[,column[,ignore_id[,id_column]]]"""
        if not args:
            return
        table = args[0]
        column = args[1] if len(args) > 1 else field
        query = f"SELECT COUNT(*) AS total FROM {table} WHERE {column} = ?"
        params: List[Any] = [value]

        if len(args) > 2 and args[2] not in ("", "null", "NULL"):
            id_column = args[3] if len(args) > 3 else "id"
            query += f" AND {id_column} <> ?"
            params.append(args[2])

        try:
            row = self._db().statement(query, params, read=True).fetchone()
        except Exception:
            return  # no database available — skip rather than reject valid data
        if row is not None and int(row["total"]) > 0:
            self._add_error(field, f"{field} has already been taken")

    def _rule_exists(self, field: str, value: Any, args: List[str]) -> None:
        """exists:table[,column]"""
        if not args:
            return
        table = args[0]
        column = args[1] if len(args) > 1 else field
        try:
            row = self._db().statement(
                f"SELECT COUNT(*) AS total FROM {table} WHERE {column} = ?",
                [value],
                read=True,
            ).fetchone()
        except Exception:
            return
        if row is None or int(row["total"]) == 0:
            self._add_error(field, f"selected {field} is invalid")

    # -- results ---------------------------------------------------------------

    def passes(self) -> bool:
        return len(self.errors) == 0

    def fails(self) -> bool:
        return not self.passes()

    def validated(self) -> Dict[str, Any]:
        """The validated subset of the input. Raises when validation failed."""
        if self.fails():
            from services.exceptions.handler import ValidationException

            raise ValidationException(self.errors)
        return {k: self.data[k] for k in self.rules if k in self.data}

    def validate(self) -> Dict[str, Any]:
        return self.validated()

    def first_error(self, field: Optional[str] = None) -> Optional[str]:
        if field is not None:
            messages = self.errors.get(field)
            return messages[0] if messages else None
        for messages in self.errors.values():
            if messages:
                return messages[0]
        return None

    def error_messages(self) -> List[str]:
        return [message for messages in self.errors.values() for message in messages]


__all__ = ["Validator"]
