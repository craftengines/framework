"""Event Dispatcher implementation for Codepy Framework."""

from typing import Any, Dict, List


class EventDispatcher:
    def __init__(self):
        self._listeners: Dict[Any, List[Any]] = {}

    def listen(self, event_cls: Any, listeners: List[Any]):
        if event_cls not in self._listeners:
            self._listeners[event_cls] = []
        self._listeners[event_cls].extend(listeners)

    def dispatch(self, event: Any):
        event_cls = event.__class__
        listeners = self._listeners.get(event_cls, [])
        for listener in listeners:
            if isinstance(listener, type):
                inst = listener()
                if hasattr(inst, "handle"):
                    inst.handle(event)
            elif callable(listener):
                listener(event)
