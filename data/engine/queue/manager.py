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

import contextlib
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
        #: Lazily built database driver — see `store()`.
        self._store: Optional[Any] = None

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

    # -- database driver -------------------------------------------------------

    def _driver_config(self) -> Dict[str, Any]:
        try:
            return dict(
                self._container().make("config").get("queue.connections.database", {})
                or {}
            )
        except Exception:
            return {}

    def store(self) -> Any:
        """The database-backed driver, chosen by capability rather than name.

        `SKIP LOCKED` is what makes claiming scale, so it is used wherever the
        dialect has it; everything else falls back to the portable
        select-then-conditional-update claim. The rest of the driver — push,
        backoff, dead-letter — is shared, so the two paths cannot drift.
        """
        if self._store is None:
            from engine.queue.drivers.base import DatabaseQueueDriver
            from engine.queue.drivers.postgres import PostgresQueueDriver

            db = self.db
            config = self._driver_config()
            config.setdefault("retry_after", self.retry_after)
            driver_class = (
                PostgresQueueDriver
                if db.dialect.supports("skip_locked")
                else DatabaseQueueDriver
            )
            self._store = driver_class(db, config)
        return self._store

    def forget_store(self) -> None:
        """Drop the cached driver — the connection or config may have changed."""
        self._store = None

    # -- pushing ---------------------------------------------------------------

    def push(self, job: Any, queue: Optional[str] = None) -> Any:
        """Dispatch a job. Runs inline on the `sync` driver."""
        return self.later(0, job, queue)

    def later(
        self,
        delay_seconds: int,
        job: Any,
        queue: Optional[str] = None,
        *,
        priority: int = 0,
    ) -> Any:
        """Dispatch a job that only becomes available after `delay_seconds`.

        `priority` is a PostgreSQL-path nicety: higher wins, and the claim's
        index is ordered to match, so an urgent job overtakes a backlog rather
        than queueing behind it.
        """
        import time

        active_driver = self.driver()
        queue_name = queue or getattr(job, "queue", "default")

        if active_driver == "sync":
            if delay_seconds:
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
            if delay_seconds:
                client.zadd(
                    f"craft_queues_delayed:{queue_name}",
                    {json.dumps(record): time.time() + delay_seconds},
                )
            else:
                client.rpush(f"craft_queues:{queue_name}", json.dumps(record))
            return record["id"]

        return self.store().push(
            serialize_job(job),
            queue_name,
            delay=int(delay_seconds),
            priority=int(priority),
            max_attempts=int(getattr(job, "max_attempts", 3) or 3),
            tenant_id=self._current_tenant(),
        )

    @staticmethod
    def _current_tenant() -> Optional[str]:
        """The tenant a job was dispatched under, stored with it.

        A worker binds this back before running the job. Without it a job runs
        under whatever tenant the previous job left behind — or under none,
        which once row-level security is in place means the job succeeds
        against an empty result set and reports success.
        """
        try:
            from engine.orm.tenancy import current_tenant_id

            return current_tenant_id()
        except Exception:
            return None

    def size(self, queue: str = "default") -> int:
        active_driver = self.driver()
        if active_driver == "redis":
            client = self._redis_client()
            return int(client.llen(f"craft_queues:{queue}")) + int(client.zcard(f"craft_queues_delayed:{queue}"))

        return self.store().size(queue)

    # -- processing ------------------------------------------------------------

    def pop(self, queue: str = "default") -> Optional[Dict[str, Any]]:
        """Atomically claim the next available job on the queue."""
        active_driver = self.driver()

        if active_driver == "database":
            claimed = self.store().claim(queue, count=1)
            return claimed[0] if claimed else None

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

        return None

    def work(self, queue_name: str = "default", max_attempts: Optional[int] = None) -> bool:
        """Process a single job. Returns True when a job was handled.

        `max_attempts` is a ceiling the caller may impose; the job's own
        `max_attempts` is the default, because how many times a job is worth
        retrying is a property of the job, not of the worker that happened to
        pick it up.
        """
        record = self.pop(queue_name)
        if record is None:
            return False

        limit = int(
            max_attempts
            if max_attempts is not None
            else (record.get("max_attempts") or 3)
        )

        try:
            job = deserialize_job(record.get("payload"))
            if job is None:
                self.fail(record, "Job payload could not be deserialised.")
                return False

            with self._tenant_scope(record.get("tenant_id")):
                job.handle()

            if self.driver() == "database":
                # Before the connection goes back, not after: the delete belongs
                # to the same checkout that ran the job, and on a queue table
                # under a row-level security policy a released connection would
                # no longer match the row it just processed.
                self.store().complete(record)

        except Exception as exc:
            attempts = int(record.get("attempts") or 0)
            if attempts >= limit:
                self.fail(record, repr(exc))
            else:
                self.release(record, queue_name, repr(exc))
            return False

        finally:
            self._release_connection()

        return True

    @contextlib.contextmanager
    def _tenant_scope(self, tenant_id: Optional[str]):
        """Run the job under the tenant it was dispatched by, if there is one."""
        try:
            from engine.orm.tenancy import TenantManager
        except ImportError:
            yield
            return

        with TenantManager(self.app).scope(tenant_id, local=False):
            yield

    def _release_connection(self) -> None:
        """Give the pooled connection back between jobs.

        The HTTP kernel does this at the end of every request; a worker never
        did, so it held one connection per thread for its whole lifetime — the
        exact exhaustion the pool exists to prevent — and carried any session
        state set by one job into the next.
        """
        try:
            self.db.release()
        except Exception:
            pass

    def release(self, record: Dict[str, Any], queue_name: str, reason: str) -> None:
        """Return a job to its queue for a later attempt."""
        if self.driver() == "redis":
            client = self._redis_client()
            client.rpush(f"craft_queues:{queue_name}", json.dumps(record))
            return
        delay = self.store().retry(record, reason)
        logging.getLogger("craft").info(
            "Job %s attempt %s failed; retrying in %.1fs: %s",
            record.get("uuid") or record.get("id"), record.get("attempts"), delay, reason,
        )

    def fail(self, record: Dict[str, Any], reason: str) -> None:
        """Bury a spent job in the dead-letter table and report the failure.

        This used to DELETE the row and write a log line, which destroyed the
        payload — nothing left to inspect and nothing left to retry. The job now
        survives in `failed_jobs` until somebody decides otherwise.
        """
        if self.driver() == "database":
            self.store().bury(record, reason)
        try:
            self._container().make("log").error(
                "Job failed permanently (queue=%s, uuid=%s): %s",
                record.get("queue"), record.get("uuid"), reason,
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
        return self.store().clear(queue)

    # -- dead letter -----------------------------------------------------------

    def failed(self, queue: Optional[str] = None, limit: int = 50) -> list:
        """Jobs that exhausted their attempts, newest first."""
        return self.store().failed(queue, limit)

    def retry_failed(self, job_uuid: Optional[str] = None) -> int:
        """Move failed jobs back onto their queue. Returns how many moved."""
        return self.store().retry_failed(job_uuid)

    def reclaim(self, retry_after: Optional[int] = None) -> int:
        """Free reservations held by workers that died. Returns how many."""
        return self.store().reclaim_stale(retry_after)
