"""LISTEN/NOTIFY loop — instant dispatch for queue work and broadcast events.

Polling costs a query per worker per interval and still delays every job by up
to that interval. A notification costs nothing while the queue is empty and
arrives the moment the inserting transaction commits.

Three constraints shape the code below, and each one is a silent failure if
missed:

  - **A dedicated connection.** A listening connection blocks for the life of
    the process. Taking one from the pool never returns it, so the pool shrinks
    by one for every listener started.
  - **Autocommit.** The driver surfaces notifications only outside a
    transaction. Without it the loop blocks forever and looks like an idle
    worker.
  - **8000 bytes.** That is the notification payload ceiling. Send an
    identifier; let the receiver read the row.

Category: Core Framework (Queue).
Relations:
  - Driven by `dev.py queue work --listen`.
  - Woken by the trigger installed in
    `database/migrations/2026_08_20_000001_rebuild_queue_tables.py`.
  - `Broadcaster` is bound as `broadcast`, exposed via the `Broadcast` facade.
References:
  - Guide: `documentation/queues_events.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import json
import logging
import select
import time
from typing import Any, Callable, Iterable, List, Optional

from engine.orm.connection import assert_schema_identifier

logger = logging.getLogger("craft")

#: Channel names are built from a queue name, so they go through the same
#: identifier check every other interpolated name in the framework does —
#: `LISTEN` takes an identifier, not a bindable parameter.
QUEUE_CHANNEL_PREFIX = "craft_queue_"


def queue_channel(queue: str) -> str:
    return assert_schema_identifier(f"{QUEUE_CHANNEL_PREFIX}{queue}")


class Listener:
    """Blocks on a PostgreSQL connection until one of its channels fires.

    `poll_interval` is a floor, not the dispatch mechanism: it bounds how long a
    notification lost to a reconnect can delay a job, and it drains work that
    was enqueued while the listener was down.
    """

    def __init__(self, db: Any, channels: Iterable[str], poll_interval: float = 5.0):
        db.dialect.require("listen_notify", "is how a worker wakes on new jobs")
        self.channels: List[str] = [assert_schema_identifier(c) for c in channels]
        if not self.channels:
            raise ValueError("A Listener needs at least one channel.")
        self.poll_interval = float(poll_interval)
        self._db = db
        self._pdo: Any = None

    # -- connection ------------------------------------------------------------

    def _connect(self) -> Any:
        import psycopg2.extensions

        pdo = self._db.write_connection.dedicated()
        pdo.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = pdo.cursor()
        try:
            for channel in self.channels:
                cursor.execute(f'LISTEN "{channel}"')
        finally:
            cursor.close()
        logger.info("Listening on %s", ", ".join(self.channels))
        return pdo

    def close(self) -> None:
        if self._pdo is not None:
            try:
                self._pdo.close()
            except Exception:
                pass
            self._pdo = None

    # -- loop ------------------------------------------------------------------

    def run(
        self,
        on_signal: Callable[[str, str], Any],
        should_stop: Callable[[], bool] = lambda: False,
    ) -> None:
        """Call `on_signal(channel, payload)` per notification, until stopped.

        A timeout is a signal too: `on_signal` fires with an empty payload so
        the caller drains its queue on a schedule even when nothing notified —
        which is what makes a lost notification a latency problem rather than a
        job that never runs.
        """
        try:
            while not should_stop():
                if self._pdo is None:
                    if not self._reconnect():
                        continue

                try:
                    ready = select.select([self._pdo], [], [], self.poll_interval)[0]
                except Exception:
                    self._drop("select failed")
                    continue

                if not ready:
                    for channel in self.channels:
                        on_signal(channel, "")
                    continue

                try:
                    self._pdo.poll()
                    notifications = list(self._pdo.notifies)
                    del self._pdo.notifies[:]
                except Exception:
                    self._drop("poll failed")
                    continue

                for note in notifications:
                    on_signal(note.channel, note.payload)
        finally:
            self.close()

    def _reconnect(self) -> bool:
        try:
            self._pdo = self._connect()
            return True
        except Exception:
            logger.warning(
                "Listener could not connect; retrying in %.1fs",
                self.poll_interval, exc_info=True,
            )
            time.sleep(self.poll_interval)
            return False

    def _drop(self, why: str) -> None:
        logger.warning("Listener connection dropped (%s); reconnecting", why, exc_info=True)
        self.close()


class Broadcaster:
    """Publish an event to every listening process, over the database.

    One less moving part than a message broker, and the publish happens inside
    the transaction that produced the event — so a client cannot be told about
    a row that then rolls back.
    """

    #: The 8000-byte notification ceiling, minus room for the envelope.
    MAX_PAYLOAD = 7_800

    def __init__(self, app: Any = None):
        self.app = app

    @property
    def db(self) -> Any:
        if self.app is not None:
            return self.app.make("db")
        from engine.container.application import Container

        return Container.getInstance().make("db")

    def publish(self, channel: str, payload: Optional[dict] = None) -> None:
        """Send `payload` to everyone listening on `channel`.

        `pg_notify()` rather than the `NOTIFY` statement: it is an ordinary
        function call, so the channel and body are bound rather than
        interpolated.
        """
        self.db.dialect.require("listen_notify", "is how Broadcast delivers events")
        assert_schema_identifier(channel)

        body = json.dumps(payload or {}, default=str)
        if len(body.encode("utf-8")) > self.MAX_PAYLOAD:
            raise ValueError(
                f"Broadcast payload is {len(body)} bytes; the notification "
                f"ceiling is 8000. Persist the body and broadcast its id."
            )
        self.db.statement("SELECT pg_notify(?, ?)", [channel, body])

    def listen(self, *channels: str, poll_interval: float = 5.0) -> Listener:
        return Listener(self.db, channels, poll_interval=poll_interval)


__all__ = ["Broadcaster", "Listener", "queue_channel"]
