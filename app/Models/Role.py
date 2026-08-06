"""Role Model for Codepy Framework RBAC."""
# Codepy Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from services.orm.model import Model


class Role(Model):
    __table__ = "roles"
    fillable = ["name", "slug"]
