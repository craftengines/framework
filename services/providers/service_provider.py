"""Base ServiceProvider for Codepy Framework."""

from typing import Any


class ServiceProvider:
    def __init__(self, app: Any):
        self.app = app

    def register(self):
        pass

    def boot(self):
        pass
