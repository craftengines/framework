"""Tests for Redis Queue Driver in Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import json
import pytest
from unittest.mock import MagicMock
from craft.queue.manager import QueueManager
from craft.queue.job import Job


class ProcessReportJob(Job):
    def __init__(self, report_id: int = 1):
        self.report_id = report_id
        self.ran = False

    def handle(self):
        self.ran = True


class FakeRedis:
    def __init__(self):
        self.lists = {}
        self.zsets = {}

    def rpush(self, key, value):
        self.lists.setdefault(key, []).append(value)
        return len(self.lists[key])

    def lpop(self, key):
        lst = self.lists.get(key, [])
        return lst.pop(0) if lst else None

    def llen(self, key):
        return len(self.lists.get(key, []))

    def zadd(self, key, mapping):
        zset = self.zsets.setdefault(key, {})
        zset.update(mapping)
        return len(mapping)

    def zcard(self, key):
        return len(self.zsets.get(key, {}))

    def zrangebyscore(self, key, min_score, max_score):
        zset = self.zsets.get(key, {})
        return [k for k, score in zset.items() if min_score <= score <= max_score]

    def zrem(self, key, member):
        zset = self.zsets.get(key, {})
        if member in zset:
            del zset[member]
            return 1
        return 0

    def delete(self, key):
        self.lists.pop(key, None)
        self.zsets.pop(key, None)


class TestRedisQueue:
    def test_redis_queue_push_and_pop(self, monkeypatch):
        fake_redis = FakeRedis()
        mgr = QueueManager()

        monkeypatch.setattr(mgr, "driver", lambda: "redis")
        monkeypatch.setattr(mgr, "_redis_client", lambda: fake_redis)

        # 1. Push
        job = ProcessReportJob(report_id=42)
        job_id = mgr.push(job, queue="reports")
        assert job_id is not None
        assert mgr.size("reports") == 1

        # 2. Pop
        record = mgr.pop("reports")
        assert record is not None
        assert record["attempts"] == 1
        assert "ProcessReportJob" in record["payload"]

        # 3. Queue is now empty
        assert mgr.size("reports") == 0

    def test_redis_queue_work_success(self, monkeypatch):
        fake_redis = FakeRedis()
        mgr = QueueManager()

        monkeypatch.setattr(mgr, "driver", lambda: "redis")
        monkeypatch.setattr(mgr, "_redis_client", lambda: fake_redis)

        job = ProcessReportJob(report_id=99)
        mgr.push(job, queue="default")

        # Execute worker
        executed = mgr.work("default")
        assert executed is True
        assert mgr.size("default") == 0
