"""ORM exceptions for Codepy Framework."""


class ORMError(Exception):
    """Base class for ORM errors."""


class ModelNotFoundError(ORMError):
    """Raised when `find_or_fail` / `first_or_fail` finds no matching record."""


class MassAssignmentError(ORMError):
    """Raised when assigning an attribute that is not fillable."""


class RelationNotFoundError(ORMError):
    """Raised when an undefined relationship is eager loaded."""
