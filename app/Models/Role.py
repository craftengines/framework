"""Role Model for Codepy Framework RBAC."""

from services.orm.model import Model


class Role(Model):
    __table__ = "roles"
    fillable = ["name", "slug"]
