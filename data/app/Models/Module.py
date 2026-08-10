"""Module model — backs the dynamic start/stop module system."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.orm.model import Model


class Module(Model):
    __table__ = "modules"

    fillable = ["name", "slug", "enabled"]

    defaults = {"enabled": True}
