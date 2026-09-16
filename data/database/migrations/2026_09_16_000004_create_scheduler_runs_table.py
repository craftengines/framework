"""Migration: once-per-window claims for `ScheduleManager.run_due_with_catchup()`.

Deploying more than one app instance, each with its own cron calling
`dev.py schedule run` every minute, runs every due task once per instance in
that same minute — `without_overlapping()` only guards a task's own previous
run still executing, not two different processes racing the same window. A
claimed row makes "did anything already run this minute's tasks" a fact in
the database, not an assumption about how many processes are watching the
clock.

Category: Framework schema (scheduling).
References:
  - Guide: `documentation/scheduling.md#multi-instance-deployments`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.facades import Schema


def up():
    Schema.create_table("scheduler_runs", lambda t: (
        # A surrogate id, not window_key as the primary key: insert_get_id()
        # always issues `RETURNING id` on PostgreSQL, so the row still needs
        # one even though every query here addresses it by window_key.
        t.id(),
        t.string("window_key", 32).unique(),
        t.timestamp("created_at"),
    ))


def down():
    Schema.drop_table("scheduler_runs")
