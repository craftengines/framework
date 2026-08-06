"""Job base class for Codepy Framework Queue system."""

from typing import Any


class ShouldQueue:
    pass


class Job:
    """Base Job class."""
    queue = "default"

    def handle(self):
        pass
