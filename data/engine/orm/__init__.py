"""ORM package exports."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from engine.orm.model import Model
from engine.orm.query_builder import QueryBuilder
from engine.orm.db import DatabaseManager
from engine.orm.connection import Connection, Row
from engine.orm.soft_deletes import SoftDeletes
from engine.orm.relationships import (
    Relation,
    HasOne,
    HasMany,
    BelongsTo,
    BelongsToMany,
)
from engine.orm.exceptions import (
    ORMError,
    ModelNotFoundError,
    MassAssignmentError,
    RelationNotFoundError,
)

__all__ = [
    "Model",
    "QueryBuilder",
    "DatabaseManager",
    "Connection",
    "Row",
    "SoftDeletes",
    "Relation",
    "HasOne",
    "HasMany",
    "BelongsTo",
    "BelongsToMany",
    "ORMError",
    "ModelNotFoundError",
    "MassAssignmentError",
    "RelationNotFoundError",
]
