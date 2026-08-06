"""Module model — backs the dynamic start/stop module system."""

from services.orm.model import Model


class Module(Model):
    __table__ = "modules"

    fillable = ["name", "slug", "enabled"]

    defaults = {"enabled": True}
