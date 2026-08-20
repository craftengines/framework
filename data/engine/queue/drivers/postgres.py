"""PostgreSQL queue driver — claims with SELECT … FOR UPDATE SKIP LOCKED.

Concurrency safety belongs to the database here, not to the worker: a candidate
row is locked for the length of the claiming statement, and `SKIP LOCKED` makes
every other worker step over it instead of queueing behind it. Two workers
cannot take the same job however they are scheduled, and adding workers adds
throughput rather than contention.

No broker, and no separate durability story either — a job and the rows it was
created alongside commit or roll back together.

Category: Core Framework (Queue).
Relations:
  - Subclasses `DatabaseQueueDriver` (`engine/queue/drivers/base.py`), which
    still owns push, retry, bury and the dead-letter table.
  - Woken by `engine/queue/listener.py` when the trigger from
    `database/migrations/2026_08_20_000001_rebuild_queue_tables.py` fires.
References:
  - Guide: `documentation/queues_events.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from typing import Any, Dict, List

from engine.queue.drivers.base import DatabaseQueueDriver, _stamp


class PostgresQueueDriver(DatabaseQueueDriver):
    """The database driver with a single statement replacing the claim loop."""

    #: One statement: a CTE picks candidates nobody else has locked, the UPDATE
    #: marks them, RETURNING hands them straight back. The ORDER BY matches
    #: `jobs_claim_idx` column for column, so the candidate scan is a seek.
    CLAIM_SQL = """
        WITH claimed AS (
            SELECT id FROM jobs
             WHERE queue = ?
               AND reserved_at IS NULL
               AND (available_at IS NULL OR available_at <= ?)
             ORDER BY priority DESC, available_at ASC, id ASC
             FOR UPDATE SKIP LOCKED
             LIMIT ?
        )
        UPDATE jobs AS j
           SET reserved_at = ?, reserved_by = ?, attempts = j.attempts + 1
          FROM claimed
         WHERE j.id = claimed.id
        RETURNING j.*
    """

    def claim(self, queue: str = "default", count: int = 1) -> List[Dict[str, Any]]:
        self.db.dialect.require(
            "skip_locked", "is how workers claim jobs without contending"
        )
        now = _stamp()
        rows = self.db.statement(
            self.CLAIM_SQL, [queue, now, int(count), now, self.worker_id]
        ).fetchall()
        return [dict(row) for row in rows]


__all__ = ["PostgresQueueDriver"]
