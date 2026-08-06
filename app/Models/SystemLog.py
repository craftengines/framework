"""SystemLog Model for Codepy Framework."""

from services.orm.model import Model


class SystemLog(Model):
    __table__ = "system_logs"

    fillable = ["level", "message", "context"]

    # `level` is NOT NULL in the schema — default it so plain message logs work.
    defaults = {"level": "info"}
