"""
Attribute conditions (ABAC) — the small predicate language attached to a grant.
Category: Core Framework (Auth).
Relations:
  - Stored in the nullable `conditions` column of `permission_user`,
    `permission_role`, `permission_group`, `group_role` and `role_user`.
  - Evaluated by `engine/auth/access.py` when resolving a permission, and
    reached from `GateManager.allows()` (`engine/auth/gate.py`).
References:
  - Guide: `documentation/authorization.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, Optional

#: Marker that makes a value refer to an attribute of the acting user rather
#: than a literal: `{"user_id": "@user.id"}` means "the resource's user_id must
#: equal the acting user's id" — ownership, expressed as data.
USER_REFERENCE_PREFIX = "@user."

_LOG = logging.getLogger("craft")


class ConditionError(ValueError):
    """A condition that cannot be understood. Raised rather than ignored.

    A malformed condition must never evaluate to "allow": that would turn a
    typo into a privilege escalation. Callers treat this as a denial and log it.
    """


def _compare_eq(actual: Any, expected: Any) -> bool:
    if actual is None or expected is None:
        return actual is expected or actual == expected
    # Ids arrive as int from one driver and str from another; comparing the
    # string forms keeps ownership checks working across SQLite/PostgreSQL/MySQL
    # without pretending 1 == "1" for genuinely different types elsewhere.
    if type(actual) is not type(expected) and isinstance(actual, (int, str)) and isinstance(expected, (int, str)):
        return str(actual) == str(expected)
    return actual == expected


#: The operator vocabulary. Deliberately small: everything here can be read at a
#: glance by whoever is auditing who can do what. Anything more expressive
#: belongs in a Policy class, which is ordinary Python and can be tested.
OPERATORS: Dict[str, Callable[[Any, Any], bool]] = {
    "eq": _compare_eq,
    "ne": lambda actual, expected: not _compare_eq(actual, expected),
    "in": lambda actual, expected: any(_compare_eq(actual, item) for item in expected),
    "not_in": lambda actual, expected: not any(_compare_eq(actual, item) for item in expected),
    "gt": lambda actual, expected: actual is not None and actual > expected,
    "gte": lambda actual, expected: actual is not None and actual >= expected,
    "lt": lambda actual, expected: actual is not None and actual < expected,
    "lte": lambda actual, expected: actual is not None and actual <= expected,
    "is_null": lambda actual, expected: (actual is None) is bool(expected),
    "contains": lambda actual, expected: actual is not None and expected in actual,
}


def parse(raw: Any) -> Optional[Dict[str, Any]]:
    """Turn a stored `conditions` value into a dict, or None when unconditional.

    Raises `ConditionError` for anything that is neither — an unreadable
    condition is a broken grant, and silently treating it as "no conditions"
    would grant more than the operator wrote down.
    """
    if raw is None or raw == "":
        return None
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", "replace")
    if isinstance(raw, str):
        try:
            decoded = json.loads(raw)
        except (TypeError, ValueError) as exc:
            raise ConditionError(f"Grant conditions are not valid JSON: {raw!r}") from exc
        if decoded is None:
            return None
        if not isinstance(decoded, dict):
            raise ConditionError(
                f"Grant conditions must be a JSON object, got {type(decoded).__name__}: {raw!r}"
            )
        return decoded
    raise ConditionError(f"Grant conditions must be a JSON object or NULL, got {type(raw).__name__}")


def dump(conditions: Optional[Dict[str, Any]]) -> Optional[str]:
    """Serialise conditions for storage. `None` stays NULL (unconditional)."""
    if conditions is None:
        return None
    if not isinstance(conditions, dict):
        raise ConditionError("Conditions must be a dict.")
    return json.dumps(conditions, sort_keys=True)


def _attribute(target: Any, name: str) -> Any:
    """Read an attribute from a model, a dict, or a plain object."""
    if target is None:
        return None
    if isinstance(target, dict):
        return target.get(name)
    getter = getattr(target, "get_attribute", None)
    if callable(getter):
        return getter(name)
    return getattr(target, name, None)


def _resolve(expected: Any, user: Any) -> Any:
    """Replace `@user.<attr>` references with the acting user's attribute."""
    if isinstance(expected, str) and expected.startswith(USER_REFERENCE_PREFIX):
        return _attribute(user, expected[len(USER_REFERENCE_PREFIX):])
    if isinstance(expected, list):
        return [_resolve(item, user) for item in expected]
    return expected


def matches(conditions: Optional[Dict[str, Any]], user: Any, resource: Any) -> bool:
    """Whether a grant's conditions hold for this user acting on this resource.

    - `None` conditions → True. The grant is unconditional.
    - Conditions present but **no resource** → False. There is nothing to check
      them against, and answering "allow" would hand out the unconditional
      version of a deliberately narrowed grant. Callers that only ask
      "does this user have the permission at all?" get the unconditional grants
      only, which is the safe reading.

    Every key must hold (AND). A key is either a literal to compare for
    equality, or a one-entry dict naming an operator::

        {"user_id": "@user.id"}                  # ownership
        {"department": "@user.department"}       # same department
        {"status": {"in": ["draft", "review"]}}  # limited to some states
        {"amount": {"lte": 10000}}               # approval ceiling
    """
    if conditions is None:
        return True
    if not conditions:
        # An empty object is not the same as NULL: someone wrote `{}` and meant
        # something. Treating it as unconditional would guess in the permissive
        # direction, so it denies.
        return False
    if resource is None:
        return False

    for attribute, expected in conditions.items():
        actual = _attribute(resource, attribute)

        if isinstance(expected, dict):
            if len(expected) != 1:
                raise ConditionError(
                    f"Condition on {attribute!r} must name exactly one operator, "
                    f"got {sorted(expected)}."
                )
            operator, operand = next(iter(expected.items()))
            if operator not in OPERATORS:
                raise ConditionError(
                    f"Unknown condition operator {operator!r} on {attribute!r}. "
                    f"Known: {', '.join(sorted(OPERATORS))}."
                )
            if not OPERATORS[operator](actual, _resolve(operand, user)):
                return False
            continue

        if not _compare_eq(actual, _resolve(expected, user)):
            return False

    return True


def matches_safely(raw: Any, user: Any, resource: Any) -> bool:
    """`matches()` for stored values: a broken condition denies, and is logged.

    Used on the resolution path, where one malformed row must not take down an
    unrelated request — but must never be read as permission either.
    """
    try:
        return matches(parse(raw), user, resource)
    except ConditionError:
        _LOG.error(
            "Ignoring a grant whose conditions could not be evaluated; treating "
            "it as denied. Fix the stored condition: %r", raw, exc_info=True,
        )
        return False


__all__ = [
    "ConditionError",
    "OPERATORS",
    "USER_REFERENCE_PREFIX",
    "dump",
    "matches",
    "matches_safely",
    "parse",
]
