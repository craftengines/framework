"""Queue Manager for Codepy Framework.

Jobs are serialised to JSON (never pickle) so a worker in another process can
rebuild them. Supported drivers: `sync` (run inline) and `database`.
"""
# Codepy Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import importlib
import json
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
        # test modules or __main__ have no importable module path).
        import sys

        for module in list(sys.modules.values()):
            candidate = getattr(module, class_name, None) if module else None
            if isinstance(candidate, type):
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
        from services.container.application import Container

        return Container.getInstance()

    @property
    def db(self) -> Any:
        return self._container().make("db")

    def driver(self) -> str:
        try:
            config = self._container().make("config")
        except Exception:
            return "sync"
        return str(
            config.get("queue.connections.default.driver")
            or config.get("queue.default")
            or "sync"
        ).lower()

    # -- pushing ---------------------------------------------------------------

    def push(self, job: Any, queue: Optional[str] = None) -> Any:
        """Dispatch a job. Runs inline on the `sync` driver."""
        queue_name = queue or getattr(job, "queue", "default")

        if self.driver() == "sync":
            job.handle()
            return None

        return self.db.statement(
            "INSERT INTO jobs (queue, payload, attempts, available_at, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            [queue_name, serialize_job(job), 0, _now(), _now()],
        )

    def later(self, delay_seconds: int, job: Any, queue: Optional[str] = None) -> Any:
        """Dispatch a job that only becomes available after `delay_seconds`."""
        from datetime import timedelta

        if self.driver() == "sync":
            job.handle()
            return None

        available_at = (
            datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=delay_seconds)
        ).isoformat()
        return self.db.statement(
            "INSERT INTO jobs (queue, payload, attempts, available_at, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            [
                queue or getattr(job, "queue", "default"),
                serialize_job(job),
                0,
                available_at,
                _now(),
            ],
        )

    def size(self, queue: str = "default") -> int:
        row = self.db.statement(
            "SELECT COUNT(*) AS total FROM jobs WHERE queue = ?", [queue], read=True
        ).fetchone()
        return int(row["total"]) if row is not None else 0

    # -- processing ------------------------------------------------------------

    def pop(self, queue: str = "default") -> Optional[Dict[str, Any]]:
        """Reserve the next available job on the queue."""
        row = self.db.statement(
            "SELECT * FROM jobs WHERE queue = ? AND (available_at IS NULL OR available_at <= ?) "
            "ORDER BY id ASC LIMIT 1",
            [queue, _now()],
            read=True,
        ).fetchone()
        return dict(row) if row is not None else None

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
            attempts = int(record.get("attempts") or 0) + 1
            if attempts >= max_attempts:
                self.fail(record, str(exc))
            else:
                self.db.statement(
                    "UPDATE jobs SET attempts = ?, reserved_at = NULL WHERE id = ?",
                    [attempts, record["id"]],
                )
            return False

        self.db.statement("DELETE FROM jobs WHERE id = ?", [record["id"]])
        return True

    def fail(self, record: Dict[str, Any], reason: str) -> None:
        """Remove a job from the queue and report the failure."""
        self.db.statement("DELETE FROM jobs WHERE id = ?", [record["id"]])
        try:
            self._container().make("log").error(
                "Job failed permanently (queue=%s): %s", record.get("queue"), reason
            )
        except Exception:
            pass

    def clear(self, queue: str = "default") -> int:
        return self.db.statement("DELETE FROM jobs WHERE queue = ?", [queue]).rowcount
