"""Automated Non-Regression Tests for Releases.

Validates that release invariants, version sync, facade contracts,
database safety rules, and anti-spam capabilities are strictly preserved.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import os
import re
import tomllib
import pytest

import craft
from craft.container.application import Container
from craft.facades import (
    AntiSpam,
    Auth,
    Cache,
    DB,
    Firewall,
    Honeypot,
    Route,
    View,
)


class TestReleaseInvariants:
    @pytest.fixture
    def pyproject_version(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        toml_path = os.path.join(root, "pyproject.toml")
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)
        return data["project"]["version"]

    def test_version_synchronized_across_package_and_pyproject(self, pyproject_version):
        """NR-01: `pyproject.toml` version must strictly match `engine.__version__`."""
        assert craft.__version__ == pyproject_version

    def test_release_counter_format(self):
        """NR-01: `__release__` must match monotonic `rNNNNN` format."""
        assert re.match(r"^r\d{5}$", craft.__release__) is not None

    def test_changelog_contains_release_entry(self):
        """NR-04: `CHANGELOG.md` must document the current release."""
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        changelog_path = os.path.join(root, "CHANGELOG.md")
        with open(changelog_path, "r", encoding="utf-8") as f:
            content = f.read()

        expected_header = f"## [{craft.__version__}] {craft.__release__}"
        assert expected_header in content
        assert "## [Unreleased]" in content


class TestDatabaseSafetyInvariants:
    def test_banned_destructive_commands_not_in_cli(self):
        """NR-02: Destructive CLI commands must never be exposed."""
        from craft.cli import app as cli_module

        # dev.py CLI commands inspectable via Typer app
        cli_app = cli_module.cli
        command_names = [cmd.name for cmd in getattr(cli_app, "registered_commands", [])]
        for banned in ["migrate:reset", "migrate:refresh", "migrate:fresh", "db:wipe", "db:drop"]:
            assert banned not in command_names, f"Banned destructive CLI command {banned} is registered!"


class TestPublicFacadeContracts:
    @pytest.mark.parametrize(
        "facade_class, expected_accessor",
        [
            (AntiSpam, "antispam"),
            (Auth, "auth"),
            (Cache, "cache"),
            (DB, "db"),
            (Firewall, "firewall"),
            (Honeypot, "honeypot"),
            (Route, "router"),
            (View, "view"),
        ],
    )
    def test_facades_accessor_stability(self, facade_class, expected_accessor):
        """NR-05: Public facades must point to stable container accessors."""
        assert facade_class.get_facade_accessor() == expected_accessor

    def test_facade_swapping_works_on_antispam(self):
        """NR-05: AntiSpam facade must support swapping for test doubles."""
        class DoubleAntiSpam:
            def verify(self, *args, **kwargs):
                return True, "MOCKED"

        double = DoubleAntiSpam()
        AntiSpam._swap(double)
        try:
            assert AntiSpam.verify({}) == (True, "MOCKED")
        finally:
            AntiSpam._clear_resolved()


class TestSecurityAndAntiSpamNonRegression:
    def test_antispam_service_available_in_container(self, migrated_database):
        """NR-06: `antispam` must be registered as singleton in container."""
        app = Container.getInstance()
        service = app.make("antispam")
        assert service is not None
        assert hasattr(service, "verify")
        assert hasattr(service, "generate_fields")

    def test_forge_has_antispam_and_error_helpers(self):
        """NR-06: Forge must provide antispam and validation error helpers."""
        from craft.view.forge import Forge

        forge = Forge()
        assert "honeypot_field" in forge.env.globals
        assert "antispam_fields" in forge.env.globals
        assert "errors" in forge.env.globals
        assert "old" in forge.env.globals
