"""Settings and Modules must actually reach the database.

Both managers fall back to in-memory state when a query fails, so the existing
subsystem test passed entirely on the memory path — the persistence it claims to
provide was never exercised. These tests read the tables back directly.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest

from craft.facades import DB, Module, Setting
from services.modules.manager import ModuleManager
from services.support.settings import SettingManager


@pytest.fixture(autouse=True)
def clean_tables(migrated_database):
    schema = migrated_database.make("schema")

    # An earlier test replaces `modules` with a reduced schema; rebuild the
    # real one so persistence is tested against what migrations actually create.
    schema.drop_table("modules")
    schema.create_table("modules", lambda t: (
        t.id(),
        t.string("name"),
        t.string("slug").unique(),
        t.boolean("enabled").default(True),
        t.timestamps(),
    ))
    DB.statement("DELETE FROM settings")
    SettingManager._memory_settings = {}

    yield

    DB.statement("DELETE FROM settings")
    SettingManager._memory_settings = {}


class TestSettingPersistence:
    def test_set_writes_a_row(self):
        Setting.set("site_title", "Craft")
        row = DB.statement(
            "SELECT value FROM settings WHERE key = ?", ["site_title"], read=True
        ).fetchone()
        assert row is not None
        assert row["value"] == '"Craft"'  # values are stored JSON-encoded

    def test_value_survives_losing_the_memory_cache(self):
        Setting.set("site_title", "Craft")
        SettingManager._memory_settings = {}
        assert Setting.get("site_title") == "Craft"

    def test_setting_the_same_key_twice_updates_it(self):
        Setting.set("site_title", "First")
        Setting.set("site_title", "Second")

        rows = DB.statement(
            "SELECT value FROM settings WHERE key = ?", ["site_title"], read=True
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]["value"] == '"Second"'  # values are stored JSON-encoded

    def test_missing_key_returns_the_default(self):
        assert Setting.get("never_set", "fallback") == "fallback"

    def test_values_keep_their_type(self):
        # Values used to be flattened through str(), so set("x", False) came
        # back as the truthy string "False". JSON encoding keeps the type.
        Setting.set("max_items", 42)
        Setting.set("feature_on", False)
        SettingManager._memory_settings = {}
        assert Setting.get("max_items") == 42
        assert Setting.get("feature_on") is False

    def test_plain_string_rows_are_read_back_as_is(self):
        # Rows written before JSON encoding hold raw strings.
        DB.statement(
            "INSERT INTO settings (key, value) VALUES (?, ?)", ["legacy", "Craft"]
        )
        assert Setting.get("legacy") == "Craft"


class TestModulePersistence:
    @pytest.fixture
    def seeded(self):
        DB.statement(
            "INSERT INTO modules (name, slug, enabled) VALUES (?, ?, ?)",
            ["Billing", "billing", True],
        )

    def _enabled_in_db(self, slug: str):
        row = DB.statement(
            "SELECT enabled FROM modules WHERE slug = ?", [slug], read=True
        ).fetchone()
        return bool(row["enabled"]) if row is not None else None

    def test_disable_writes_to_the_database(self, seeded):
        Module.disable("billing")
        assert self._enabled_in_db("billing") is False

    def test_enable_writes_to_the_database(self, seeded):
        Module.disable("billing")
        Module.enable("billing")
        assert self._enabled_in_db("billing") is True

    def test_is_enabled_reads_from_the_database(self, seeded):
        DB.statement("UPDATE modules SET enabled = ? WHERE slug = ?", [False, "billing"])
        assert Module.is_enabled("billing") is False

    def test_all_lists_database_modules(self, seeded):
        slugs = [m["slug"] for m in Module.all()]
        assert "billing" in slugs

    def test_enabling_an_unknown_module_reports_failure(self):
        # It used to return True unconditionally, so a typo in the slug looked
        # like a successful call.
        assert ModuleManager().enable("does-not-exist") is False

    def test_disabling_an_unknown_module_reports_failure(self):
        assert ModuleManager().disable("does-not-exist") is False

    def test_an_in_memory_module_can_still_be_toggled(self):
        manager = ModuleManager()
        manager.register("inmem", "In Memory")
        assert manager.disable("inmem") is True
        assert manager.is_enabled("inmem") is False

    def test_unknown_module_is_not_enabled(self):
        assert ModuleManager().is_enabled("does-not-exist") is False
