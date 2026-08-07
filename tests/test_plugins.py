"""Plugin manager: registration, activation and hooks."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import logging

import pytest

from services.plugins.manager import PluginManager


@pytest.fixture
def plugins():
    return PluginManager()


class TestRegistration:
    def test_a_registered_plugin_is_active(self, plugins):
        plugins.register("stripe", {"version": "1.0"})
        assert plugins.is_active("stripe") is True

    def test_an_unknown_plugin_is_not_active(self, plugins):
        assert plugins.is_active("nope") is False

    def test_all_lists_registered_plugins(self, plugins):
        plugins.register("a", {})
        plugins.register("b", {})
        assert {p["name"] for p in plugins.all()} == {"a", "b"}

    def test_deactivate_then_activate(self, plugins):
        plugins.register("stripe", {})
        plugins.deactivate("stripe")
        assert plugins.is_active("stripe") is False
        plugins.activate("stripe")
        assert plugins.is_active("stripe") is True

    def test_registering_twice_replaces_the_entry(self, plugins):
        plugins.register("stripe", {"version": "1"})
        plugins.register("stripe", {"version": "2"})
        assert len(plugins.all()) == 1
        assert plugins.all()[0]["instance"]["version"] == "2"


class TestHooks:
    def test_a_hook_receives_the_arguments(self, plugins):
        seen = []
        plugins.add_hook("payment", lambda amount, currency=None: seen.append((amount, currency)))
        plugins.trigger_hook("payment", 150.0, currency="BRL")
        assert seen == [(150.0, "BRL")]

    def test_hooks_run_in_registration_order(self, plugins):
        order = []
        plugins.add_hook("e", lambda: order.append(1))
        plugins.add_hook("e", lambda: order.append(2))
        plugins.trigger_hook("e")
        assert order == [1, 2]

    def test_results_are_collected(self, plugins):
        plugins.add_hook("e", lambda: "a")
        plugins.add_hook("e", lambda: "b")
        assert plugins.trigger_hook("e") == ["a", "b"]

    def test_triggering_an_unregistered_hook_is_harmless(self, plugins):
        assert plugins.trigger_hook("nothing-here") == []

    def test_has_hook(self, plugins):
        assert plugins.has_hook("e") is False
        plugins.add_hook("e", lambda: None)
        assert plugins.has_hook("e") is True

    def test_remove_a_single_hook(self, plugins):
        keep = lambda: "keep"  # noqa: E731
        drop = lambda: "drop"  # noqa: E731
        plugins.add_hook("e", keep)
        plugins.add_hook("e", drop)
        plugins.remove_hook("e", drop)
        assert plugins.trigger_hook("e") == ["keep"]

    def test_remove_every_hook_for_an_event(self, plugins):
        plugins.add_hook("e", lambda: None)
        plugins.remove_hook("e")
        assert plugins.has_hook("e") is False


class TestHookFailureIsolation:
    def test_one_failing_plugin_does_not_stop_the_others(self, plugins):
        def explodes():
            raise RuntimeError("bad plugin")

        plugins.add_hook("e", explodes)
        plugins.add_hook("e", lambda: "survivor")

        assert plugins.trigger_hook("e") == ["survivor"]

    def test_the_failure_is_logged_not_swallowed(self, plugins, caplog):
        def explodes():
            raise RuntimeError("bad plugin")

        plugins.add_hook("payment", explodes)
        with caplog.at_level(logging.WARNING, logger="craft"):
            plugins.trigger_hook("payment")

        assert any("payment" in record.message for record in caplog.records)

    def test_the_exception_does_not_propagate(self, plugins):
        plugins.add_hook("e", lambda: 1 / 0)
        plugins.trigger_hook("e")  # must not raise
