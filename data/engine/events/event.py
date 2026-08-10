"""
Event — Optional base class for event objects (plain data carriers; events can
also be plain strings).
Category: Core Framework (Events).
Relations:
  - Dispatched through `engine/events/dispatcher.py`.
References:
  - Guide: `documentation/queues_events.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

class Event:
    """Base class for event objects.

    Subclasses may set `name` to a stable string. The dispatcher matches
    string-registered listeners against it (`dispatcher._matches`), which is
    what lets plugin hooks — which are keyed by name, not by class — listen to
    the same events as typed listeners without a second dispatch path.
    """

    #: Stable string identity. `None` means "match by class only".
    name: str = None
