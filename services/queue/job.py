"""Job base class for Codepy Framework Queue system."""
# Codepy Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from typing import Any


class ShouldQueue:
    pass


class Job:
    """Base Job class."""
    queue = "default"

    def handle(self):
        pass
