"""Permission Model for Codepy Framework RBAC."""

from services.orm.model import Model


class Permission(Model):
    __table__ = "permissions"
    fillable = ["name", "slug"]
