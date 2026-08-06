"""SystemLog Model for Codepy Framework."""
# Codepy Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from services.orm.model import Model


class SystemLog(Model):
    __table__ = "system_logs"

    fillable = ["level", "message", "context"]

    # `level` is NOT NULL in the schema — default it so plain message logs work.
    defaults = {"level": "info"}
