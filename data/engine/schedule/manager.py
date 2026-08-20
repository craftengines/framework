"""
ScheduleManager — registers recurring tasks and runs the ones due right now.
Category: Core Framework (Scheduling).
Relations:
  - Bound as `schedule` by `engine/providers/service_providers.py`, reached
    through the `Schedule` facade.
  - Tasks are declared in `routes/console.py`.
  - `dev.py schedule run` asks for the due tasks and executes them; `dev.py
    schedule list` prints the registry.
  - `without_overlapping()` takes its lock from the `cache` binding.
References:
  - Guide: `documentation/scheduling.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import logging
import subprocess
import sys
from datetime import datetime
from typing import Any, Callable, List, Optional

logger = logging.getLogger("craft")


def _match_field(expression: str, value: int) -> bool:
    """Match one cron field against one value.

    Supports the four forms that cover every frequency helper below —
    `*`, `a,b,c`, `a-b`, and `*/n` (also `a-b/n`) — so the helpers are thin
    sugar over a single matcher rather than fifteen bespoke predicates.
    """
    for part in str(expression).split(","):
        part = part.strip()
        if not part:
            continue

        step = 1
        if "/" in part:
            part, _, step_text = part.partition("/")
            try:
                step = int(step_text)
            except ValueError:
                continue
            if step <= 0:
                continue

        if part in ("*", ""):
            if value % step == 0:
                return True
            continue

        if "-" in part:
            low_text, _, high_text = part.partition("-")
            try:
                low, high = int(low_text), int(high_text)
            except ValueError:
                continue
            if low <= value <= high and (value - low) % step == 0:
                return True
            continue

        try:
            if int(part) == value:
                return True
        except ValueError:
            continue

    return False


class ScheduledTask:
    """One recurring task: what to run, and the cron expression saying when.

    Frequency helpers mutate the five cron fields and return `self`, so they
    chain: `Schedule.command("emails:send").daily_at("02:00")`.
    """

    def __init__(self, kind: str, target: Any, manager: "ScheduleManager"):
        self.kind = kind              # "command" | "call" | "job"
        self.target = target
        self._manager = manager

        # Defaults to every minute — the loosest schedule, narrowed by helpers.
        self.minute = "*"
        self.hour = "*"
        self.day_of_month = "*"
        self.month = "*"
        self.day_of_week = "*"

        self._constraints: List[Callable[[], bool]] = []
        self._overlap_lock_minutes: Optional[int] = None
        self._description: Optional[str] = None

    # -- identity ----------------------------------------------------------

    @property
    def name(self) -> str:
        if self._description:
            return self._description
        if self.kind == "command":
            return f"command: {self.target}"
        if self.kind == "job":
            return f"job: {type(self.target).__name__}"
        return f"call: {getattr(self.target, '__qualname__', repr(self.target))}"

    def described_as(self, description: str) -> "ScheduledTask":
        self._description = description
        return self

    @property
    def expression(self) -> str:
        return (
            f"{self.minute} {self.hour} {self.day_of_month} "
            f"{self.month} {self.day_of_week}"
        )

    # -- frequency ---------------------------------------------------------

    def cron(self, expression: str) -> "ScheduledTask":
        """Set all five fields from a raw cron expression."""
        fields = expression.split()
        if len(fields) != 5:
            raise ValueError(
                f"A cron expression needs 5 fields, got {len(fields)}: {expression!r}"
            )
        (
            self.minute,
            self.hour,
            self.day_of_month,
            self.month,
            self.day_of_week,
        ) = fields
        return self

    def every_minute(self) -> "ScheduledTask":
        return self.cron("* * * * *")

    def every_minutes(self, minutes: int) -> "ScheduledTask":
        """Every N minutes — the general form behind the fixed-interval helpers."""
        if minutes <= 0:
            raise ValueError("minutes must be positive")
        return self.cron(f"*/{minutes} * * * *")

    def every_five_minutes(self) -> "ScheduledTask":
        return self.every_minutes(5)

    def every_ten_minutes(self) -> "ScheduledTask":
        return self.every_minutes(10)

    def every_fifteen_minutes(self) -> "ScheduledTask":
        return self.every_minutes(15)

    def every_thirty_minutes(self) -> "ScheduledTask":
        return self.every_minutes(30)

    def hourly(self) -> "ScheduledTask":
        return self.cron("0 * * * *")

    def hourly_at(self, minute: int) -> "ScheduledTask":
        return self.cron(f"{int(minute)} * * * *")

    def daily(self) -> "ScheduledTask":
        return self.cron("0 0 * * *")

    def daily_at(self, time: str) -> "ScheduledTask":
        """`daily_at("02:30")` — hour and minute, 24-hour clock."""
        hour, _, minute = time.partition(":")
        return self.cron(f"{int(minute or 0)} {int(hour)} * * *")

    def weekly(self) -> "ScheduledTask":
        return self.cron("0 0 * * 0")

    def monthly(self) -> "ScheduledTask":
        return self.cron("0 0 1 * *")

    def quarterly(self) -> "ScheduledTask":
        return self.cron("0 0 1 1,4,7,10 *")

    def yearly(self) -> "ScheduledTask":
        return self.cron("0 0 1 1 *")

    def weekdays(self) -> "ScheduledTask":
        self.day_of_week = "1-5"
        return self

    def weekends(self) -> "ScheduledTask":
        self.day_of_week = "0,6"
        return self

    def days(self, *day_numbers: int) -> "ScheduledTask":
        """Restrict to specific weekdays (0 = Sunday)."""
        self.day_of_week = ",".join(str(int(d)) for d in day_numbers)
        return self

    def at(self, time: str) -> "ScheduledTask":
        """Pin the time of day, keeping the existing day constraints.

        Lets `weekly().sundays().at("03:00")` read the way it does in the
        design doc without each day helper having to re-specify the time.
        """
        hour, _, minute = time.partition(":")
        self.hour = str(int(hour))
        self.minute = str(int(minute or 0))
        return self

    # -- constraints -------------------------------------------------------

    def when(self, callback: Callable[[], bool]) -> "ScheduledTask":
        """Run only when `callback()` is truthy at execution time."""
        self._constraints.append(callback)
        return self

    def skip(self, callback: Callable[[], bool]) -> "ScheduledTask":
        """The inverse of `when` — skip while `callback()` is truthy."""
        self._constraints.append(lambda: not callback())
        return self

    def without_overlapping(self, minutes: int = 60) -> "ScheduledTask":
        """Refuse to start while a previous run is still going.

        Matters because cron fires `schedule run` every minute: a task that
        takes longer than its interval would otherwise pile up copies of
        itself. The lock expires after `minutes` so a crashed run cannot block
        the task forever.
        """
        self._overlap_lock_minutes = minutes
        return self

    # -- evaluation --------------------------------------------------------

    def is_due(self, now: datetime) -> bool:
        """Does this task's cron expression match `now`, to the minute?"""
        # Cron weekdays are 0=Sunday; Python's weekday() is 0=Monday.
        cron_weekday = (now.weekday() + 1) % 7
        return (
            _match_field(self.minute, now.minute)
            and _match_field(self.hour, now.hour)
            and _match_field(self.day_of_month, now.day)
            and _match_field(self.month, now.month)
            and _match_field(self.day_of_week, cron_weekday)
        )

    def filters_pass(self) -> bool:
        """Evaluate `when`/`skip` constraints. A raising constraint blocks the
        task — running on an unknown condition is the riskier default."""
        for constraint in self._constraints:
            try:
                if not constraint():
                    return False
            except Exception:
                logger.warning(
                    "Constraint raised for scheduled task %s; skipping it",
                    self.name, exc_info=True,
                )
                return False
        return True

    # -- execution ---------------------------------------------------------

    @property
    def lock_key(self) -> str:
        return f"schedule:lock:{self.name}"

    def run(self) -> Any:
        """Execute the task, honouring its overlap lock."""
        if self._overlap_lock_minutes is None:
            return self._execute()

        lock = self._manager.lock()
        if lock is not None and lock.supported():
            # A transaction-scoped advisory lock: two schedulers racing the same
            # minute genuinely serialise, and a run that crashes releases the
            # lock when its connection drops rather than blocking the task until
            # an arbitrary TTL expires.
            with lock.transaction(self.lock_key) as held:
                if not held:
                    logger.info(
                        "Skipping %s — another run holds the lock", self.name
                    )
                    return None
                return self._execute()

        return self._run_with_cache_lock()

    def _run_with_cache_lock(self) -> Any:
        """Fallback for drivers without advisory locks.

        `Cache.add()` is an atomic put-if-absent. The `has()` then `put()` pair
        this replaces was a check-then-set race: two schedulers both saw no lock
        and both ran, so the guarantee the method name makes did not hold. It is
        still weaker than an advisory lock — a crashed run holds the key until
        it expires — which is why it is the fallback and not the mechanism.
        """
        cache = self._manager.cache()
        if cache is None:
            return self._execute()

        if not cache.add(self.lock_key, "1", self._overlap_lock_minutes * 60):
            logger.info("Skipping %s — previous run still holds the lock", self.name)
            return None
        try:
            return self._execute()
        finally:
            cache.forget(self.lock_key)

    def _execute(self) -> Any:
        if self.kind == "call":
            return self.target()

        if self.kind == "job":
            queue = self._manager.queue()
            if queue is None:
                raise RuntimeError("No queue is bound; cannot schedule a job")
            return queue.push(self.target)

        # A command runs in its own process: an artisan-style task that calls
        # sys.exit() or crashes must not take the scheduler down with it.
        completed = subprocess.run(
            [sys.executable, "dev.py", *self.target.split()],
            cwd=self._manager.base_path(),
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            logger.warning(
                "Scheduled command %r exited %s: %s",
                self.target, completed.returncode, completed.stderr.strip(),
            )
        return completed


class ScheduleManager:
    """The registry of scheduled tasks, and the runner for the ones due now."""

    def __init__(self, app: Any = None):
        self.app = app
        self._tasks: List[ScheduledTask] = []

    # -- container access (tolerant: the scheduler is usable standalone) ----

    def _make(self, key: str) -> Any:
        if self.app is None:
            return None
        try:
            return self.app.make(key)
        except Exception:
            return None

    def cache(self) -> Any:
        return self._make("cache")

    def queue(self) -> Any:
        return self._make("queue")

    def lock(self) -> Any:
        return self._make("lock")

    def base_path(self) -> str:
        return getattr(self.app, "base_path", None) or "."

    # -- registration ------------------------------------------------------

    def command(self, command: str) -> ScheduledTask:
        """Schedule a `dev.py` command, e.g. `Schedule.command("queue work")`."""
        return self._add(ScheduledTask("command", command, self))

    def call(self, callback: Callable[[], Any]) -> ScheduledTask:
        """Schedule a Python callable."""
        return self._add(ScheduledTask("call", callback, self))

    def job(self, job: Any) -> ScheduledTask:
        """Schedule a queue job — pushed onto the queue when due."""
        return self._add(ScheduledTask("job", job, self))

    def _add(self, task: ScheduledTask) -> ScheduledTask:
        self._tasks.append(task)
        return task

    def tasks(self) -> List[ScheduledTask]:
        return list(self._tasks)

    def flush(self) -> None:
        self._tasks.clear()

    # -- execution ---------------------------------------------------------

    def due_tasks(self, now: Optional[datetime] = None) -> List[ScheduledTask]:
        now = now or datetime.now()
        return [
            task for task in self._tasks
            if task.is_due(now) and task.filters_pass()
        ]

    def run_due(self, now: Optional[datetime] = None) -> List[str]:
        """Run every task due at `now`, and return the names that ran.

        One failing task must not stop the rest: cron gives the scheduler a
        single shot per minute, so an exception escaping here would silently
        drop every task queued behind it.
        """
        ran: List[str] = []
        for task in self.due_tasks(now):
            try:
                task.run()
                ran.append(task.name)
            except Exception:
                logger.warning(
                    "Scheduled task %s raised", task.name, exc_info=True
                )
        return ran


__all__ = ["ScheduleManager", "ScheduledTask"]
