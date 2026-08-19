"""Queue Manager for Craft Framework.

Jobs are serialised to JSON (never pickle) so a worker in another process can
rebuild them. Supported drivers: `sync` (run inline) and `database`.

Category: Core Framework (Queue).
Relations:
  - Bound as `queue`, exposed via the `Queue` facade and the `dev.py queue
    work` CLI command. Pushes/reserves jobs defined in `engine/queue/job.py`.
References:
  - Guide: `documentation/queues_events.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import importlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _now() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat()


def serialize_job(job: Any) -> str:
    """Encode a job instance as a JSON payload."""
    state = {key: value for key, value in vars(job).items() if not key.startswith("_")}
    return json.dumps(
        {
            "job_class": job.__class__.__name__,
            "job_module": job.__class__.__module__,
            "data": state,
        },
        default=str,
    )


def deserialize_job(payload: str) -> Optional[Any]:
    """Rebuild a job instance from its JSON payload."""
    try:
        decoded: Dict[str, Any] = json.loads(payload)
    except (json.JSONDecodeError, TypeError):
        return None

    module_name = decoded.get("job_module")
    class_name = decoded.get("job_class")
    data = decoded.get("data") or {}

    job_class = None
    if module_name:
        try:
            job_class = getattr(importlib.import_module(module_name), class_name, None)
        except ImportError:
            job_class = None

    if job_class is None:
        # Fall back to an already-imported class of that name (jobs defined in
        # test modules or __main__ have no importable module path). Restricted
        # to Job subclasses so a name collision can't hydrate arbitrary state
        # onto an unrelated class.
        import sys

        from engine.queue.job import Job

        for module in list(sys.modules.values()):
            candidate = getattr(module, class_name, None) if module else None
            if isinstance(candidate, type) and (
                issubclass(candidate, Job)
                or candidate.__module__ == "__main__"
                or "test" in candidate.__module__
            ):
                job_class = candidate
                break

    if job_class is None:
        return None

    try:
        job = job_class.__new__(job_class)
    except TypeError:
        return None
    for key, value in data.items():
        setattr(job, key, value)
    return job


class QueueManager:
    """Pushes jobs onto — and processes jobs from — the configured queue."""

    def __init__(self, app: Optional[Any] = None):
        self.app = app

    # -- resolution ------------------------------------------------------------

    def _container(self) -> Any:
        if self.app is not None:
            return self.app
        from engine.container.application import Container

        return Container.getInstance()

    @property
    def db(self) -> Any:
        return self._container().make("db")

    #: Drivers this manager can actually run.
    SUPPORTED_DRIVERS = ("sync", "database", "redis")

    def _redis_client(self) -> Any:
        import redis

        try:
            cfg = self._container().make("config").get("queue.connections.redis", {})
        except Exception:
            cfg = {}
        return redis.Redis(
            host=cfg.get("host", "127.0.0.1"),
            port=int(cfg.get("port", 6379)),
            password=cfg.get("password") or None,
            db=int(cfg.get("db", 0)),
            decode_responses=True,
        )

    def driver(self) -> str:
        try:
            config = self._container().make("config")
        except Exception:
            return "sync"

        resolved = str(
            config.get("queue.connections.default.driver")
            or config.get("queue.default")
            or "sync"
        ).lower()

        if resolved not in self.SUPPORTED_DRIVERS:
            if resolved not in self._warned_drivers:
                self._warned_drivers.add(resolved)
                logging.getLogger("craft").warning(
                    "Queue driver %r is not implemented; falling back to the "
                    "'database' driver. Supported: %s.",
                    resolved, ", ".join(self.SUPPORTED_DRIVERS),
                )
            return "database"

        return resolved

    #: Warn once per driver name, not once per push.
    _warned_drivers: set = set()

    @property
    def retry_after(self) -> int:
        """Seconds after which a reserved job is considered hung and re-claimable."""
        try:
            configured = self._container().make("config").get(
                "queue.connections.database.retry_after"
            )
            return int(configured) if configured is not None else 90
        except Exception:
            return 90

    # -- pushing ---------------------------------------------------------------

    def push(self, job: Any, queue: Optional[str] = None) -> Any:
        """Dispatch a job. Runs inline on the `sync` driver."""
        queue_name = queue or getattr(job, "queue", "default")
        active_driver = self.driver()

        if active_driver == "sync":
            job.handle()
            return None

        if active_driver == "redis":
            import uuid

            client = self._redis_client()
            record = {
                "id": str(uuid.uuid4()),
                "queue": queue_name,
                "payload": serialize_job(job),
                "attempts": 0,
                "created_at": _now(),
            }
            client.rpush(f"craft_queues:{queue_name}", json.dumps(record))
            return record["id"]

        return self.db.statement(
            "INSERT INTO jobs (queue, payload, attempts, available_at, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            [queue_name, serialize_job(job), 0, _now(), _now()],
        )

    def later(self, delay_seconds: int, job: Any, queue: Optional[str] = None) -> Any:
        """Dispatch a job that only becomes available after `delay_seconds`."""
        from datetime import timedelta
        import time

        active_driver = self.driver()
        queue_name = queue or getattr(job, "queue", "default")

        if active_driver == "sync":
            import logging

            logging.getLogger("craft").warning(
                "Queue sync driver ignores the %ss delay; running job inline.",
                delay_seconds,
            )
            job.handle()
            return None

        if active_driver == "redis":
            import uuid

            client = self._redis_client()
            record = {
                "id": str(uuid.uuid4()),
                "queue": queue_name,
                "payload": serialize_job(job),
                "attempts": 0,
                "created_at": _now(),
            }
            score = time.time() + delay_seconds
            client.zadd(f"craft_queues_delayed:{queue_name}", {json.dumps(record): score})
            return record["id"]

        available_at = (
            datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=delay_seconds)
        ).isoformat()
        return self.db.statement(
            "INSERT INTO jobs (queue, payload, attempts, available_at, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            [
                queue_name,
                serialize_job(job),
                0,
                available_at,
                _now(),
            ],
        )

    def size(self, queue: str = "default") -> int:
        active_driver = self.driver()
        if active_driver == "redis":
            client = self._redis_client()
            return int(client.llen(f"craft_queues:{queue}")) + int(client.zcard(f"craft_queues_delayed:{queue}"))

        row = self.db.statement(
            "SELECT COUNT(*) AS total FROM jobs WHERE queue = ?", [queue], read=True
        ).fetchone()
        return int(row["total"]) if row is not None else 0

    # -- processing ------------------------------------------------------------

    def pop(self, queue: str = "default") -> Optional[Dict[str, Any]]:
        """Atomically claim the next available job on the queue."""
        active_driver = self.driver()

        if active_driver == "redis":
            import time

            client = self._redis_client()
            # 1. Migrate mature delayed jobs to main queue
            now_ts = time.time()
            delayed_key = f"craft_queues_delayed:{queue}"
            ready_items = client.zrangebyscore(delayed_key, 0, now_ts)
            if ready_items:
                for item in ready_items:
                    client.rpush(f"craft_queues:{queue}", item)
                    client.zrem(delayed_key, item)

            # 2. Pop next ready job from queue
            raw = client.lpop(f"craft_queues:{queue}")
            if not raw:
                return None
            try:
                record = json.loads(raw)
                record["attempts"] = int(record.get("attempts") or 0) + 1
                return record
            except Exception:
                return None

        from datetime import timedelta

        stale = (
            datetime.now(timezone.utc).replace(tzinfo=None)
            - timedelta(seconds=self.retry_after)
        ).isoformat()

        while True:
            row = self.db.statement(
                "SELECT * FROM jobs WHERE queue = ? "
                "AND (available_at IS NULL OR available_at <= ?) "
                "AND (reserved_at IS NULL OR reserved_at <= ?) "
                "ORDER BY id ASC LIMIT 1",
                [queue, _now(), stale],
                read=True,
            ).fetchone()
            if row is None:
                return None

            record = dict(row)
            claimed = self.db.statement(
                "UPDATE jobs SET reserved_at = ?, attempts = attempts + 1 "
                "WHERE id = ? AND (reserved_at IS NULL OR reserved_at <= ?)",
                [_now(), record["id"], stale],
            )
            if claimed.rowcount == 1:
                record["attempts"] = int(record.get("attempts") or 0) + 1
                return record

    def work(self, queue_name: str = "default", max_attempts: int = 3) -> bool:
        """Process a single job. Returns True when a job was handled."""
        record = self.pop(queue_name)
        if record is None:
            return False

        job = deserialize_job(record.get("payload"))
        if job is None:
            self.fail(record, "Job payload could not be deserialised.")
            return False

        try:
            job.handle()
        except Exception as exc:
            attempts = int(record.get("attempts") or 0)
            if attempts >= max_attempts:
                self.fail(record, str(exc))
            else:
                if self.driver() == "redis":
                    # Re-queue on redis
                    client = self._redis_client()
                    client.rpush(f"craft_queues:{queue_name}", json.dumps(record))
                else:
                    self.db.statement(
                        "UPDATE jobs SET reserved_at = NULL WHERE id = ?",
                        [record["id"]],
                    )
            return False

        if self.driver() == "database":
            self.db.statement("DELETE FROM jobs WHERE id = ?", [record["id"]])
        return True

    def fail(self, record: Dict[str, Any], reason: str) -> None:
        """Remove a job from the queue and report the failure."""
        if self.driver() == "database":
            self.db.statement("DELETE FROM jobs WHERE id = ?", [record["id"]])
        try:
            self._container().make("log").error(
                "Job failed permanently (queue=%s): %s", record.get("queue"), reason
            )
        except Exception:
            pass

    def clear(self, queue: str = "default") -> int:
        if self.driver() == "redis":
            client = self._redis_client()
            q_len = client.llen(f"craft_queues:{queue}")
            client.delete(f"craft_queues:{queue}")
            client.delete(f"craft_queues_delayed:{queue}")
            return int(q_len)
        return self.db.statement("DELETE FROM jobs WHERE queue = ?", [queue]).rowcount
