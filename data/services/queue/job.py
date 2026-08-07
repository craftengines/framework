"""
Job — Base class for queued jobs. Subclasses implement a synchronous
`handle()`, never `async def` — the worker calls it directly.
Category: Core Framework (Queue).
Relations:
  - Pushed via `services/queue/manager.py` / the `Queue` facade; must accept
    only JSON-serialisable constructor arguments (no Model instances).
References:
  - Guide: `documentation/queues_events.md`
"""
# Craft Framework
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
