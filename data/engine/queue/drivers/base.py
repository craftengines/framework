"""Queue driver contract and the portable database implementation.

A driver owns four things and nothing else: putting a job on the queue,
claiming one exclusively, releasing it for a later attempt, and burying it when
its attempts are spent. Deserialising and running the job is the manager's job
(`engine/queue/manager.py`), so a new driver never has to reimplement it.

Category: Core Framework (Queue).
Relations:
  - Selected by `QueueManager._driver_instance()`.
  - `engine/queue/drivers/postgres.py` overrides only `claim()`.
References:
  - Guide: `documentation/queues_events.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import os
import random
import socket
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


def _now() -> datetime:
    """UTC, naive — the shape every timestamp in this framework is stored in."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _stamp(moment: Optional[datetime] = None) -> str:
    return (moment or _now()).isoformat()


@runtime_checkable
class QueueDriver(Protocol):
    """What the manager may assume about any queue backend."""

    def push(self, payload: str, queue: str, *, delay: int, priority: int,
             max_attempts: int, tenant_id: Optional[str]) -> Any: ...

    def claim(self, queue: str, count: int) -> List[Dict[str, Any]]: ...

    def complete(self, record: Dict[str, Any]) -> None: ...

    def retry(self, record: Dict[str, Any], error: str) -> float: ...

    def bury(self, record: Dict[str, Any], error: str) -> None: ...

    def size(self, queue: str) -> int: ...

    def clear(self, queue: str) -> int: ...


class DatabaseQueueDriver:
    """The portable driver: works on every supported database.

    Claiming is a `SELECT` of the next candidate followed by a conditional
    `UPDATE` that only succeeds if nobody else reserved it first. That is
    correct on any driver, but every worker contends on the same head row, so
    throughput falls as workers are added. `PostgresQueueDriver` replaces just
    this step with `FOR UPDATE SKIP LOCKED`, where the database hands each
    worker a *different* row instead.
    """

    def __init__(self, db: Any, config: Optional[Dict[str, Any]] = None) -> None:
        self.db = db
        self.config = dict(config or {})
        #: Recorded in `jobs.reserved_by`, so a stuck queue can be traced to a
        #: host and a pid rather than guessed at.
        self.worker_id = f"{socket.gethostname()}:{os.getpid()}"[:128]

    # -- tuning ----------------------------------------------------------------

    @property
    def retry_after(self) -> int:
        """Seconds after which a reservation is assumed to belong to a dead worker."""
        return int(self.config.get("retry_after") or 90)

    @property
    def backoff_base(self) -> int:
        return int(self.config.get("backoff_base") or 5)

    @property
    def backoff_cap(self) -> int:
        return int(self.config.get("backoff_cap") or 3600)

    # -- pushing ---------------------------------------------------------------

    def push(
        self,
        payload: str,
        queue: str = "default",
        *,
        delay: int = 0,
        priority: int = 0,
        max_attempts: int = 3,
        tenant_id: Optional[str] = None,
    ) -> Any:
        import uuid

        job_uuid = str(uuid.uuid4())
        available_at = _stamp(_now() + timedelta(seconds=int(delay)))
        self.db.statement(
            "INSERT INTO jobs "
            "  (uuid, queue, payload, attempts, priority, max_attempts, "
            "   tenant_id, available_at, created_at) "
            "VALUES (?, ?, ?, 0, ?, ?, ?, ?, ?)",
            [
                job_uuid, queue, payload, int(priority), int(max_attempts),
                tenant_id, available_at, _stamp(),
            ],
        )
        return job_uuid

    # -- claiming --------------------------------------------------------------

    def claim(self, queue: str = "default", count: int = 1) -> List[Dict[str, Any]]:
        claimed: List[Dict[str, Any]] = []
        while len(claimed) < count:
            record = self._claim_one(queue)
            if record is None:
                break
            claimed.append(record)
        return claimed

    def _claim_one(self, queue: str) -> Optional[Dict[str, Any]]:
        while True:
            row = self.db.statement(
                "SELECT * FROM jobs WHERE queue = ? "
                "  AND (available_at IS NULL OR available_at <= ?) "
                "  AND reserved_at IS NULL "
                "ORDER BY priority DESC, available_at ASC, id ASC LIMIT 1",
                [queue, _stamp()],
                read=True,
            ).fetchone()
            if row is None:
                return None

            record = dict(row)
            claimed = self.db.statement(
                "UPDATE jobs SET reserved_at = ?, reserved_by = ?, "
                "  attempts = attempts + 1 "
                "WHERE id = ? AND reserved_at IS NULL",
                [_stamp(), self.worker_id, record["id"]],
            )
            if claimed.rowcount == 1:
                record["attempts"] = int(record.get("attempts") or 0) + 1
                record["reserved_by"] = self.worker_id
                return record
            # Someone else took it between the SELECT and the UPDATE. Look again
            # rather than returning None — the queue is not empty, just busy.

    # -- completion ------------------------------------------------------------

    def complete(self, record: Dict[str, Any]) -> None:
        self.db.statement("DELETE FROM jobs WHERE id = ?", [record["id"]])

    def retry(self, record: Dict[str, Any], error: str) -> float:
        """Release the job for a later attempt, backed off, and return the delay.

        Full jitter rather than a fixed curve: a hundred jobs that failed
        together against one downed dependency must not all wake at the same
        instant and knock it over again. The old behaviour — clearing
        `reserved_at` immediately — burned every attempt in milliseconds, so a
        thirty-second outage killed jobs that a single retry would have saved.
        """
        attempt = max(1, int(record.get("attempts") or 1))
        ceiling = min(self.backoff_base * (2 ** (attempt - 1)), self.backoff_cap)
        delay = random.uniform(0, ceiling)

        self.db.statement(
            "UPDATE jobs SET reserved_at = NULL, reserved_by = NULL, "
            "  last_error = ?, available_at = ? WHERE id = ?",
            [error[:4000], _stamp(_now() + timedelta(seconds=delay)), record["id"]],
        )
        return delay

    def bury(self, record: Dict[str, Any], error: str) -> None:
        """Move a spent job to the dead-letter table, atomically.

        The insert and the delete are one transaction because they are one
        decision. Doing them separately means a crash in between either loses
        the job or duplicates it, and the whole point of this table is that a
        failed job survives to be looked at.
        """
        def move() -> None:
            self.db.statement(
                "INSERT INTO failed_jobs "
                "  (uuid, queue, payload, attempts, tenant_id, exception, failed_at) "
                "SELECT uuid, queue, payload, attempts, tenant_id, ?, ? "
                "  FROM jobs WHERE id = ?",
                [error[:8000], _stamp(), record["id"]],
            )
            self.db.statement("DELETE FROM jobs WHERE id = ?", [record["id"]])

        self.db.transaction(move)

    # -- maintenance -----------------------------------------------------------

    def reclaim_stale(self, retry_after: Optional[int] = None) -> int:
        """Free reservations held by workers that died mid-flight.

        A scheduled task, not part of the claim. Folding `reserved_at <= stale`
        into the claim predicate is what the previous implementation did, and it
        is why no index could cover it: the hot path paid for a rare event on
        every single claim.
        """
        cutoff = _stamp(_now() - timedelta(seconds=retry_after or self.retry_after))
        return self.db.statement(
            "UPDATE jobs SET reserved_at = NULL, reserved_by = NULL "
            "WHERE reserved_at IS NOT NULL AND reserved_at < ?",
            [cutoff],
        ).rowcount or 0

    def size(self, queue: str = "default") -> int:
        row = self.db.statement(
            "SELECT COUNT(*) AS total FROM jobs WHERE queue = ?", [queue], read=True
        ).fetchone()
        return int(row["total"]) if row is not None else 0

    def clear(self, queue: str = "default") -> int:
        return self.db.statement("DELETE FROM jobs WHERE queue = ?", [queue]).rowcount or 0

    # -- dead letter -----------------------------------------------------------

    def failed(self, queue: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        if queue:
            rows = self.db.statement(
                "SELECT * FROM failed_jobs WHERE queue = ? ORDER BY id DESC LIMIT ?",
                [queue, int(limit)], read=True,
            ).fetchall()
        else:
            rows = self.db.statement(
                "SELECT * FROM failed_jobs ORDER BY id DESC LIMIT ?",
                [int(limit)], read=True,
            ).fetchall()
        return [dict(row) for row in rows]

    def retry_failed(self, job_uuid: Optional[str] = None) -> int:
        """Move failed jobs back onto their queue, attempts reset.

        One transaction per call so a partial re-queue cannot leave a job in
        both tables.
        """
        where, params = ("WHERE uuid = ?", [job_uuid]) if job_uuid else ("", [])
        moved = 0

        def move() -> None:
            nonlocal moved
            result = self.db.statement(
                "INSERT INTO jobs "
                "  (uuid, queue, payload, attempts, priority, max_attempts, "
                "   tenant_id, available_at, created_at) "
                f"SELECT uuid, queue, payload, 0, 0, 3, tenant_id, ?, ? "
                f"  FROM failed_jobs {where}",
                [_stamp(), _stamp(), *params],
            )
            moved = result.rowcount or 0
            self.db.statement(f"DELETE FROM failed_jobs {where}", list(params))

        self.db.transaction(move)
        return moved


__all__ = ["DatabaseQueueDriver", "QueueDriver"]
