"""ORM exceptions for Codepy Framework."""
# Codepy Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.


class ORMError(Exception):
    """Base class for ORM errors."""


class ModelNotFoundError(ORMError):
    """Raised when `find_or_fail` / `first_or_fail` finds no matching record."""


class MassAssignmentError(ORMError):
    """Raised when assigning an attribute that is not fillable."""


class RelationNotFoundError(ORMError):
    """Raised when an undefined relationship is eager loaded."""
