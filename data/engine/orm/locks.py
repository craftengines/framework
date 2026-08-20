"""Distributed locks on PostgreSQL advisory locks.

    from craft.facades import Lock

    with Lock.transaction("invoices:close:2026-08") as held:
        if not held:
            return
        close_the_month()

    Lock.key("reports:nightly").get(build_report)          # skip if held
    Lock.key("ledger").block_for(10).get(post_entries)     # wait, then give up

An advisory lock costs no table, no row and no cleanup job, and the database
releases it when the connection dies — which a cache TTL cannot promise. That
last property is the whole reason this exists: a lock whose holder crashed must
not block the work until an arbitrary expiry passes.

Category: Core Framework (ORM).
Relations:
  - Bound as `lock`, exposed via the `Lock` facade.
  - `ScheduledTask.without_overlapping()` (`engine/schedule/manager.py`) uses
    it, falling back to `Cache.add()` where advisory locks do not exist.
References:
  - Guide: `documentation/orm.md#distributed-locks`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import contextlib
import hashlib
import logging
from typing import Any, Callable, Iterator, List, Optional

logger = logging.getLogger("craft")

_SIGN_BIT = 1 << 63
_UINT64 = 1 << 64


def key_to_bigint(key: str) -> int:
    """Hash a human-readable key to the signed 64-bit integer the locks take.

    blake2b truncated to eight bytes. Collision probability stays negligible at
    any realistic number of distinct keys, and unlike a pair of crc32 values it
    does not cluster on long structured keys like
    `tenant:0f3a…:invoices:close`. A collision is safe but surprising — two
    unrelated keys would serialise against each other — so `LockManager.explain`
    prints the integer for anyone debugging one.
    """
    if not isinstance(key, str) or not key:
        raise ValueError("A lock key must be a non-empty string.")
    digest = hashlib.blake2b(key.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big", signed=True)


class LockHandle:
    """One named lock, configured fluently, then acquired."""

    def __init__(self, manager: "LockManager", key: str):
        self._manager = manager
        self.key = key
        self.id = key_to_bigint(key)
        self._wait_seconds: Optional[float] = None

    def block_for(self, seconds: float) -> "LockHandle":
        """Wait up to `seconds` for the lock instead of failing immediately.

        Implemented with `lock_timeout` rather than a Python retry loop: the
        wait happens inside the database, so the caller is woken the instant the
        holder releases rather than on the next poll tick.
        """
        if seconds <= 0:
            raise ValueError("block_for() needs a positive number of seconds.")
        self._wait_seconds = float(seconds)
        return self

    # -- acquisition -----------------------------------------------------------

    def acquire(self) -> bool:
        """Take the lock. False means somebody else holds it.

        Session-scoped, so it survives across statements — and so it is held by
        the *connection*. Anything acquired here must be released here; see
        `LockManager.transaction` for the variant that cannot be left behind.
        """
        db = self._manager.db
        db.dialect.require("advisory_locks", "back the Lock facade")

        if self._wait_seconds is None:
            row = db.statement("SELECT pg_try_advisory_lock(?) AS ok", [self.id]).fetchone()
            return bool(row["ok"])

        db.statement(
            "SELECT set_config('lock_timeout', ?, false)",
            [f"{int(self._wait_seconds * 1000)}ms"],
        )
        try:
            db.statement("SELECT pg_advisory_lock(?)", [self.id])
            return True
        except Exception:
            # `lock_timeout` fired. Not an error the caller needs a traceback
            # for — "somebody else has it" is a normal answer.
            logger.debug("Timed out waiting for lock %r", self.key)
            return False
        finally:
            db.statement("SELECT set_config('lock_timeout', '0', false)")

    def release(self) -> bool:
        """Give the lock back. False means this connection did not hold it."""
        row = self._manager.db.statement(
            "SELECT pg_advisory_unlock(?) AS ok", [self.id]
        ).fetchone()
        return bool(row["ok"])

    def get(self, callback: Callable[[], Any]) -> Any:
        """Run `callback` under the lock, or return None if it is held.

        The distinction matters: None means "somebody else has it", which for a
        scheduled report is success, not failure. The release is in a `finally`,
        so an exception inside the callback frees the lock on its way out.
        """
        if not self.acquire():
            return None
        try:
            return callback()
        finally:
            self.release()

    @contextlib.contextmanager
    def hold(self) -> Iterator[bool]:
        """Context-manager form of `get()`, yielding whether it was acquired."""
        acquired = self.acquire()
        try:
            yield acquired
        finally:
            if acquired:
                self.release()


class LockManager:
    """Named locks, hashed to advisory lock ids."""

    def __init__(self, app: Any = None):
        self.app = app

    @property
    def db(self) -> Any:
        if self.app is not None:
            return self.app.make("db")
        from engine.container.application import Container

        return Container.getInstance().make("db")

    def supported(self) -> bool:
        """Whether the active driver can lock at all — for a fallback path."""
        return self.db.dialect.supports("advisory_locks")

    def key(self, key: str) -> LockHandle:
        return LockHandle(self, key)

    @contextlib.contextmanager
    def transaction(self, key: str, *, wait: bool = False) -> Iterator[bool]:
        """Hold a transaction-scoped lock for the block. The safe default.

            with Lock.transaction("ledger:post") as held:
                if not held:
                    return
                post_entries()

        A session lock lives on the connection, so returning that connection to
        the pool while it is held leaves the lock outstanding, invisibly, until
        the pooled connection is closed. A transaction lock is released by the
        database at COMMIT or ROLLBACK with no cooperation required — including
        when the process dies mid-block, which is exactly the case a TTL-based
        lock cannot rule out.
        """
        db = self.db
        db.dialect.require("advisory_locks", "back Lock.transaction")
        lock_id = key_to_bigint(key)

        db.begin_transaction()
        try:
            function = "pg_advisory_xact_lock" if wait else "pg_try_advisory_xact_lock"
            row = db.statement(f"SELECT {function}(?) AS ok", [lock_id]).fetchone()
            held = True if wait else bool(row["ok"])
            yield held
            db.commit()
        except Exception:
            db.rollback()
            raise

    def run(self, key: str, callback: Callable[[], Any], *, wait: bool = False) -> Any:
        """`transaction()` as a call: run `callback` under the lock, or None."""
        with self.transaction(key, wait=wait) as held:
            return callback() if held else None

    # -- diagnosis -------------------------------------------------------------

    def explain(self, key: str) -> dict:
        """The integer a key hashes to, and which backends hold it.

        For the two questions a stuck lock raises: is anyone actually holding
        this, and did two unrelated keys collide onto one id?
        """
        lock_id = key_to_bigint(key)
        holders: List[dict] = []
        if self.supported():
            rows = self.db.statement(
                "SELECT pid, classid, objid, granted FROM pg_locks "
                "WHERE locktype = 'advisory'",
                read=True,
            ).fetchall()
            for row in rows:
                # A single-argument advisory lock is stored split across
                # classid (high 32 bits) and objid (low 32), unsigned.
                combined = (int(row["classid"]) << 32) | int(row["objid"])
                if combined >= _SIGN_BIT:
                    combined -= _UINT64
                if combined == lock_id:
                    holders.append({"pid": row["pid"], "granted": bool(row["granted"])})
        return {"key": key, "id": lock_id, "holders": holders}


__all__ = ["LockHandle", "LockManager", "key_to_bigint"]
