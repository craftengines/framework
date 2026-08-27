"""Cooperative shutdown for long-running foreground processes.

A queue worker or a scheduler is killed by the orchestrator on every deploy.
Killed mid-job, the job stays reserved until the stale-reservation sweep
reclaims it minutes later, and any side effect it had already performed
happens twice when it runs again. Catching the signal and finishing the job in
hand costs one loop iteration and removes both.

Category: Core Framework (Support).
Relations:
  - Used by the `queue work` and `schedule work` commands in
    `engine/cli/app.py`.
References:
  - Guide: `documentation/queues.md`, `documentation/deployment.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import signal
import threading
from types import FrameType
from typing import Any, Callable, Optional

#: The signals an orchestrator sends before it resorts to SIGKILL. SIGTERM is
#: what Docker, systemd and Kubernetes send; SIGINT is Ctrl-C.
_STOP_SIGNALS = ("SIGTERM", "SIGINT")


class ShutdownSignal:
    """An event set when the process is asked to stop.

    Used as a loop condition rather than a callback, so a worker decides for
    itself where the safe stopping point is:

        stop = ShutdownSignal().install()
        while not stop.requested:
            process_one_job()
            stop.wait(1.0)

    A second signal is left to the default handler, so an operator who sends
    SIGTERM twice still gets an immediate exit rather than a process that
    ignores them.
    """

    def __init__(self, on_signal: Optional[Callable[[str], None]] = None):
        self._event = threading.Event()
        self._on_signal = on_signal
        self._previous: dict = {}

    @property
    def requested(self) -> bool:
        return self._event.is_set()

    def install(self) -> "ShutdownSignal":
        """Take over the stop signals, if this thread may (the main one)."""
        for name in _STOP_SIGNALS:
            number = getattr(signal, name, None)
            if number is None:  # pragma: no cover - platform dependent
                continue
            try:
                self._previous[number] = signal.signal(number, self._handle)
            except ValueError:  # pragma: no cover - not the main thread
                continue
        return self

    def restore(self) -> None:
        """Put the previous handlers back."""
        for number, handler in self._previous.items():
            try:
                signal.signal(number, handler)
            except ValueError:  # pragma: no cover - not the main thread
                continue
        self._previous.clear()

    def wait(self, seconds: float) -> bool:
        """Sleep, waking early if a stop is requested. True when it was."""
        return self._event.wait(timeout=seconds)

    def _handle(self, number: int, frame: Optional[FrameType]) -> None:
        name = signal.Signals(number).name
        # Restore first: a second signal must not be swallowed by this handler.
        self.restore()
        self._event.set()
        if self._on_signal is not None:
            self._on_signal(name)

    def __enter__(self) -> "ShutdownSignal":
        return self.install()

    def __exit__(self, *exc: Any) -> None:
        self.restore()
