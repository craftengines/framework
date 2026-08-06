"""Translation model — backs the `__()` translation helper."""

from services.orm.model import Model


class Translation(Model):
    __table__ = "translations"

    fillable = ["key", "locale", "value"]
