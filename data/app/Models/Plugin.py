"""Plugin model — backs the disk-discovered, DB-persisted plugin registry."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.orm.model import Model


class Plugin(Model):
    __table__ = "plugins"

    fillable = ["name", "slug", "enabled", "path"]

    defaults = {"enabled": True}
