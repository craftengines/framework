"""
Task scheduling — cron-style recurring tasks.
Category: Core Framework (Scheduling).
Relations:
  - Bound as `schedule` and exposed via the `Schedule` facade.
  - Tasks are declared in `routes/console.py`, loaded at boot by
    `FrameworkSubsystemsServiceProvider`.
  - Executed by `dev.py schedule run`, which system cron calls every minute.
References:
  - Guide: `documentation/scheduling.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from engine.schedule.manager import ScheduledTask, ScheduleManager

__all__ = ["ScheduleManager", "ScheduledTask"]
