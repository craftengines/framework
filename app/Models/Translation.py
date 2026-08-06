"""Translation model — backs the `__()` translation helper."""
# Codepy Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from services.orm.model import Model


class Translation(Model):
    __table__ = "translations"

    fillable = ["key", "locale", "value"]
