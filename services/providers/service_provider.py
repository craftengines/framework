"""Base ServiceProvider for Codepy Framework."""
# Codepy Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from typing import Any


class ServiceProvider:
    def __init__(self, app: Any):
        self.app = app

    def register(self):
        pass

    def boot(self):
        pass
