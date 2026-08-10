"""The task scheduler.

Until this landed, `schedule` was bound to a placebo: a nested class whose
`hourly()`/`daily()` returned `self` and which never ran anything. Tasks
declared in `routes/console.py` were doubly dead — nothing called
`register_console()` either, so the registry was always empty.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from datetime import datetime

import pytest

from craft.schedule.manager import ScheduleManager, _match_field


class TestCronFieldMatching:
    """One matcher backs every frequency helper, so it carries the weight."""

    @pytest.mark.parametrize("expression,value,expected", [
        ("*", 0, True),
        ("*", 37, True),
        ("5", 5, True),
        ("5", 6, False),
        ("1,15,30", 15, True),
        ("1,15,30", 16, False),
        ("10-20", 15, True),
        ("10-20", 21, False),
        ("*/15", 0, True),
        ("*/15", 30, True),
        ("*/15", 31, False),
        ("*/5", 20, True),
    ])
    def test_it_matches_each_cron_form(self, expression, value, expected):
        assert _match_field(expression, value) is expected

    def test_malformed_fields_do_not_match_rather_than_raise(self):
        # A typo in a cron expression must not take the whole scheduler down
        # on every minute-tick.
        assert _match_field("abc", 5) is False
        assert _match_field("*/0", 5) is False


class TestFrequencyHelpers:
    @pytest.fixture
    def manager(self):
        return ScheduleManager()

    def test_default_is_every_minute(self, manager):
        assert manager.call(lambda: None).expression == "* * * * *"

    @pytest.mark.parametrize("build,expected", [
        (lambda t: t.hourly(), "0 * * * *"),
        (lambda t: t.hourly_at(15), "15 * * * *"),
        (lambda t: t.daily(), "0 0 * * *"),
        (lambda t: t.daily_at("02:30"), "30 2 * * *"),
        (lambda t: t.every_fifteen_minutes(), "*/15 * * * *"),
        (lambda t: t.weekly(), "0 0 * * 0"),
        (lambda t: t.monthly(), "0 0 1 * *"),
        (lambda t: t.yearly(), "0 0 1 1 *"),
        (lambda t: t.weekdays(), "* * * * 1-5"),
        (lambda t: t.weekly().days(0).at("03:00"), "0 3 * * 0"),
    ])
    def test_helpers_produce_the_documented_expression(self, manager, build, expected):
        assert build(manager.call(lambda: None)).expression == expected

    def test_a_bad_cron_expression_is_rejected_loudly(self, manager):
        with pytest.raises(ValueError):
            manager.call(lambda: None).cron("* * *")


class TestDueEvaluation:
    @pytest.fixture
    def manager(self):
        return ScheduleManager()

    def test_hourly_is_due_only_on_the_hour(self, manager):
        task = manager.call(lambda: None).hourly()
        assert task.is_due(datetime(2026, 8, 10, 14, 0)) is True
        assert task.is_due(datetime(2026, 8, 10, 14, 1)) is False

    def test_daily_at_is_due_only_at_that_time(self, manager):
        task = manager.call(lambda: None).daily_at("02:30")
        assert task.is_due(datetime(2026, 8, 10, 2, 30)) is True
        assert task.is_due(datetime(2026, 8, 10, 3, 30)) is False

    def test_weekdays_excludes_the_weekend(self, manager):
        task = manager.call(lambda: None).weekdays()
        # 2026-08-10 is a Monday; 2026-08-09 a Sunday.
        assert task.is_due(datetime(2026, 8, 10, 9, 0)) is True
        assert task.is_due(datetime(2026, 8, 9, 9, 0)) is False

    def test_sunday_maps_to_cron_zero_not_python_six(self, manager):
        """Python counts Monday as 0, cron counts Sunday as 0. Getting this
        backwards silently shifts every day-constrained task by one day."""
        task = manager.call(lambda: None).days(0)
        assert task.is_due(datetime(2026, 8, 9, 0, 0)) is True   # Sunday
        assert task.is_due(datetime(2026, 8, 10, 0, 0)) is False  # Monday


class TestConstraints:
    @pytest.fixture
    def manager(self):
        return ScheduleManager()

    def test_when_blocks_a_task_whose_condition_is_false(self, manager):
        ran = []
        manager.call(lambda: ran.append(1)).every_minute().when(lambda: False)
        assert manager.run_due(datetime(2026, 8, 10, 12, 0)) == []
        assert ran == []

    def test_skip_is_the_inverse_of_when(self, manager):
        ran = []
        manager.call(lambda: ran.append(1)).every_minute().skip(lambda: True)
        manager.run_due(datetime(2026, 8, 10, 12, 0))
        assert ran == []

    def test_a_raising_constraint_blocks_rather_than_runs(self, manager):
        """Running on an unknown condition is the riskier default — a task
        gated on 'is this the primary node?' must not fire when that check
        itself breaks."""
        ran = []

        def broken():
            raise RuntimeError("cannot determine")

        manager.call(lambda: ran.append(1)).every_minute().when(broken)
        assert manager.run_due(datetime(2026, 8, 10, 12, 0)) == []
        assert ran == []


class TestRunning:
    @pytest.fixture
    def manager(self):
        return ScheduleManager()

    def test_it_runs_the_due_task_and_reports_it(self, manager):
        ran = []
        manager.call(lambda: ran.append("yes")).every_minute().described_as("tick")

        names = manager.run_due(datetime(2026, 8, 10, 12, 0))

        assert ran == ["yes"]
        assert names == ["tick"]

    def test_it_leaves_undue_tasks_alone(self, manager):
        ran = []
        manager.call(lambda: ran.append(1)).daily_at("02:00")
        manager.run_due(datetime(2026, 8, 10, 12, 0))
        assert ran == []

    def test_one_failing_task_does_not_stop_the_others(self, manager):
        """Cron gives the scheduler a single shot per minute — an exception
        escaping the loop would silently drop every task behind it."""
        ran = []

        def explodes():
            raise RuntimeError("task is broken")

        manager.call(explodes).every_minute().described_as("bad")
        manager.call(lambda: ran.append("survivor")).every_minute().described_as("good")

        names = manager.run_due(datetime(2026, 8, 10, 12, 0))

        assert ran == ["survivor"]
        assert names == ["good"]

    def test_a_job_without_a_queue_is_reported_not_silently_dropped(self, manager):
        manager.job(object()).every_minute()
        # Surfaces as a caught-and-logged failure, so the task simply does not
        # appear in the "ran" list rather than appearing to have succeeded.
        assert manager.run_due(datetime(2026, 8, 10, 12, 0)) == []


class TestOverlapPrevention:
    """cron fires `schedule run` every minute; a task slower than its interval
    would otherwise stack copies of itself."""

    class FakeCache:
        def __init__(self):
            self.store = {}

        def has(self, key):
            return key in self.store

        def put(self, key, value, ttl=None):
            self.store[key] = value

        def forget(self, key):
            self.store.pop(key, None)

    @pytest.fixture
    def manager(self):
        cache = self.FakeCache()
        manager = ScheduleManager()
        manager.cache = lambda: cache
        manager._cache = cache
        return manager

    def test_it_skips_while_a_previous_run_holds_the_lock(self, manager):
        ran = []
        task = manager.call(lambda: ran.append(1)).every_minute().without_overlapping()

        manager._cache.put(task.lock_key, "1")
        task.run()

        assert ran == []

    def test_the_lock_is_released_after_a_successful_run(self, manager):
        task = manager.call(lambda: None).every_minute().without_overlapping()
        task.run()
        assert manager._cache.has(task.lock_key) is False

    def test_the_lock_is_released_even_when_the_task_raises(self, manager):
        """A crashed run must not block the task forever."""
        def explodes():
            raise RuntimeError("boom")

        task = manager.call(explodes).every_minute().without_overlapping()
        with pytest.raises(RuntimeError):
            task.run()

        assert manager._cache.has(task.lock_key) is False


class TestRegistry:
    def test_tasks_are_listed_with_their_expression(self):
        manager = ScheduleManager()
        manager.command("queue work").every_five_minutes()
        manager.call(lambda: None).daily()

        tasks = manager.tasks()
        assert len(tasks) == 2
        assert tasks[0].name == "command: queue work"
        assert tasks[0].expression == "*/5 * * * *"

    def test_the_bound_scheduler_is_the_real_one_not_a_placebo(self, migrated_database):
        """Guards the regression that motivated this work: `schedule` used to
        resolve to a stub whose frequency methods did nothing."""
        from craft.container.application import Container

        scheduler = Container.getInstance().make("schedule")
        assert isinstance(scheduler, ScheduleManager)
        assert hasattr(scheduler, "run_due")
