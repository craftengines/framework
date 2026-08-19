"""Regressions for framework promises that were not being kept.

Each test here maps to something the framework advertised — a facade method, a
config key, a feature flag, a CLI guarantee — that silently did nothing. They
are grouped in one file because they share a cause rather than a subsystem:
code that looked implemented from the outside.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import os

import pytest

from craft.facades import Cache, DB


class TestFacadeSwap:
    """`Facade._swap()` was `pass`, so a test double never took effect and the
    "mocked" facade went on calling the real service."""

    def test_a_swapped_double_receives_the_calls(self):
        class FakeCache:
            def __init__(self):
                self.calls = []

            def get(self, key, default=None):
                self.calls.append(key)
                return "from-the-double"

        double = FakeCache()
        Cache._swap(double)
        try:
            assert Cache.get("anything") == "from-the-double"
            assert double.calls == ["anything"]
        finally:
            Cache._clear_resolved()

    def test_clearing_restores_the_real_service(self, migrated_database):
        class FakeCache:
            def get(self, key, default=None):
                return "double"

        Cache._swap(FakeCache())
        Cache._clear_resolved()

        Cache.put("real-key", "real-value")
        assert Cache.get("real-key") == "real-value"

    def test_a_swap_on_one_facade_does_not_leak_to_another(self, migrated_database):
        """Storing the double on the shared base class would rewire every
        facade in the process at once."""
        class FakeCache:
            def get(self, key, default=None):
                return "double"

        Cache._swap(FakeCache())
        try:
            # DB must still be the real binding.
            assert not isinstance(DB.__dict__.get("_swapped"), FakeCache)
            assert DB.statement("SELECT 1 AS one", read=True).fetchone() is not None
        finally:
            Cache._clear_resolved()


class TestConfigKeysThatAreActuallyRead:
    """Several keys were read under names the config repository never creates,
    so they silently resolved to their defaults forever."""

    @pytest.fixture
    def config(self, migrated_database):
        from craft.container.application import Container

        return Container.getInstance().make("config")

    def test_app_release_resolves(self, config):
        """The layout footer and version badge render `config('app.release')`;
        it had no declaration at all, so both showed blank."""
        assert config.get("app.release") is not None

    def test_version_has_a_single_source_of_truth(self, config):
        """`config/framework.py` carried a hand-maintained copy that had
        already drifted from the package (r00002 vs the real r00001)."""
        import craft

        assert config.get("app.release") == craft.__release__
        assert config.get("framework.FRAMEWORK_RELEASE") == craft.__release__
        assert config.get("app.version") == craft.__version__

    def test_debug_resolves_under_the_name_the_repository_creates(self, config):
        """`app.debug` never existed — the repository keys entries by the
        module attribute name — so debug mode could not be turned on."""
        assert config.get("app.APP_DEBUG") is not None
        assert config.get("app.debug", "<<missing>>") == "<<missing>>"


class TestQueueDriverHonesty:
    @pytest.fixture
    def queue(self, migrated_database):
        from craft.container.application import Container

        return Container.getInstance().make("queue")

    def test_an_unimplemented_driver_does_not_masquerade_as_working(self, queue, monkeypatch):
        """Unimplemented driver (e.g. SQS) warns and falls back to database driver."""
        from craft.container.application import Container

        config = Container.getInstance().make("config")
        monkeypatch.setitem(config._items["queue"], "default", "sqs")

        assert queue.driver() == "database"
        assert "sqs" not in queue.SUPPORTED_DRIVERS
        assert "redis" in queue.SUPPORTED_DRIVERS

    def test_retry_after_comes_from_config(self, queue):
        """It was hardcoded to 90, so the declared knob did nothing."""
        from craft.container.application import Container

        config = Container.getInstance().make("config")
        assert queue.retry_after == config.get("queue.connections.database.retry_after")


class TestCacheDriverHonesty:
    def test_an_unknown_driver_warns_instead_of_silently_using_memory(self, caplog):
        """A typo in CACHE_DRIVER used to look exactly like a working cache,
        which quietly makes rate limiting per-process."""
        from craft.cache.manager import CacheManager
        from craft.container.application import Container

        app = Container.getInstance()
        config = app.make("config")
        original = config._items["cache"].get("default")
        config._items["cache"]["default"] = "not-a-real-driver"
        try:
            with caplog.at_level("WARNING", logger="craft"):
                CacheManager(app)._resolve_store()
            assert any("Unknown cache driver" in r.message for r in caplog.records)
        finally:
            config._items["cache"]["default"] = original


class TestGeneratorsRefuseToOverwrite:
    """`documentation/cli.md` promises "generators refuse to overwrite".
    `generate_migration` did not, which is worst on a migration: the old one
    may already have run in production."""

    def test_a_second_migration_with_the_same_name_is_refused(self, tmp_path):
        from craft.cli import generators

        generators.generate_migration("create_widgets_table", str(tmp_path))

        # The filename carries a timestamp, so force the collision by reusing
        # the exact path the generator just produced.
        directory = os.path.join(str(tmp_path), "database", "migrations")
        existing = os.listdir(directory)[0]
        name = existing[len("YYYY_MM_DD_HHMMSS_"):-3]

        from craft.migrations.migrator import migration_filename

        if migration_filename(name) == existing:
            with pytest.raises(FileExistsError):
                generators.generate_migration(name, str(tmp_path))

    def test_force_allows_the_overwrite(self, tmp_path):
        from craft.cli import generators

        path = generators.generate_migration("create_gadgets_table", str(tmp_path))
        # Same second, same filename: with force it must succeed.
        again = generators.generate_migration(
            "create_gadgets_table", str(tmp_path), force=True
        )
        assert os.path.exists(again) and os.path.exists(path)


class TestGeneratedPolicyFailsClosed:
    def test_the_policy_stub_does_not_authorize_everyone(self):
        """A generated policy that returned True everywhere handed you a file
        that looked like protection while granting universal access."""
        from craft.cli.generators import policy_stub

        source = policy_stub("PostPolicy")
        namespace = {}
        exec(compile(source, "<policy_stub>", "exec"), namespace)
        policy = namespace["PostPolicy"]()

        assert policy.update(None, object()) is False
        assert policy.delete(None, object()) is False
        assert policy.view(None, object()) is False
        # Anonymous callers are never authorised, even for the open abilities.
        assert policy.view_any(None) is False
        assert policy.create(None) is False


class TestConfigKeysThatNothingRead:
    """Three keys were declared in `config/` and read by nothing at all, so a
    developer could change them and observe no effect anywhere."""

    def test_app_url_prefixes_absolute_route_urls(self, migrated_database):
        from craft.facades import Config, Route

        Route.get("/absolute-url-probe", lambda: "ok").name("probe.absolute")

        router = migrated_database.make("router")
        original = Config.get("app.APP_URL")
        Config.set("app.APP_URL", "https://example.test/")
        try:
            assert router.absolute_url_for("probe.absolute") == "https://example.test/absolute-url-probe"
            # The relative form is untouched.
            assert router.url_for("probe.absolute") == "/absolute-url-probe"
        finally:
            Config.set("app.APP_URL", original)

    def test_default_guard_selects_the_provider(self, migrated_database):
        """`auth.defaults.guard` and each guard's `provider` were decorative —
        the user model was read straight from `auth.providers.users.model`."""
        from craft.facades import Config

        auth = migrated_database.make("auth")
        assert auth.provider_name() == Config.get("auth.guards.web.provider")
        assert auth.provider_name("api") == Config.get("auth.guards.api.provider")

        original = Config.get("auth.defaults.guard")
        Config.set("auth.guards.admin", {"driver": "session", "provider": "admins"})
        Config.set("auth.defaults.guard", "admin")
        try:
            assert auth.provider_name() == "admins"
        finally:
            Config.set("auth.defaults.guard", original)
            Config.set("auth.guards.admin", None)

    def test_the_unwired_keys_are_gone(self):
        """`APP_TIMEZONE` and `password_timeout` were removed rather than left
        as knobs with no wiring — Craft stores timestamps in UTC and has no
        confirm-password window."""
        from craft.facades import Config

        assert Config.get("app.APP_TIMEZONE") is None
        assert Config.get("auth.password_timeout") is None
