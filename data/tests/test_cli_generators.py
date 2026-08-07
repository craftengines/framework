"""craft make:* generators."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import os

import pytest

from services.cli import generators


class TestNaming:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("product", "Product"),
            ("service_order", "ServiceOrder"),
            ("service-order", "ServiceOrder"),
            ("ServiceOrder", "ServiceOrder"),
        ],
    )
    def test_studly(self, value, expected):
        assert generators.studly(value) == expected

    @pytest.mark.parametrize(
        "value,expected",
        [("Product", "product"), ("ServiceOrder", "service_order"), ("API", "a_p_i")],
    )
    def test_snake(self, value, expected):
        assert generators.snake(value) == expected

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("product", "products"),
            ("cemetery", "cemeteries"),
            ("box", "boxes"),
            ("dish", "dishes"),
            ("day", "days"),
        ],
    )
    def test_plural(self, value, expected):
        assert generators.plural(value) == expected

    def test_table_for_model(self):
        assert generators.table_for("ServiceOrder") == "service_orders"


class TestGenerate:
    def test_model_lands_in_app_models(self, tmp_path):
        path = generators.generate("model", "widget", str(tmp_path))
        assert path.endswith(os.path.join("app", "Models", "Widget.py"))
        assert "class Widget(Model)" in open(path, encoding="utf-8").read()

    def test_model_gets_the_pluralised_table(self, tmp_path):
        path = generators.generate("model", "cemetery", str(tmp_path))
        assert '__table__ = "cemeteries"' in open(path, encoding="utf-8").read()

    def test_controller_suffix_is_added_once(self, tmp_path):
        first = generators.generate("controller", "Widget", str(tmp_path))
        assert first.endswith("WidgetController.py")
        os.remove(first)
        second = generators.generate("controller", "WidgetController", str(tmp_path))
        assert second.endswith("WidgetController.py")

    def test_resource_controller_has_crud_methods(self, tmp_path):
        path = generators.generate("controller", "Widget", str(tmp_path), resource=True)
        source = open(path, encoding="utf-8").read()
        for method in ("index", "show", "store", "update", "destroy"):
            assert f"async def {method}" in source

    def test_plain_controller_has_no_crud(self, tmp_path):
        path = generators.generate("controller", "Widget", str(tmp_path))
        assert "async def destroy" not in open(path, encoding="utf-8").read()

    def test_refuses_to_overwrite(self, tmp_path):
        generators.generate("model", "Widget", str(tmp_path))
        with pytest.raises(FileExistsError):
            generators.generate("model", "Widget", str(tmp_path))

    def test_force_overwrites(self, tmp_path):
        generators.generate("model", "Widget", str(tmp_path))
        assert generators.generate("model", "Widget", str(tmp_path), force=True)

    def test_unknown_kind_raises(self, tmp_path):
        with pytest.raises(ValueError):
            generators.generate("nonsense", "Widget", str(tmp_path))

    @pytest.mark.parametrize(
        "kind,directory",
        [
            ("middleware", os.path.join("app", "Http", "Middleware")),
            ("request", os.path.join("app", "Http", "Requests")),
            ("job", os.path.join("app", "Jobs")),
            ("policy", os.path.join("app", "Policies")),
            ("seeder", os.path.join("database", "seeders")),
            ("factory", os.path.join("database", "factories")),
        ],
    )
    def test_each_kind_lands_in_its_directory(self, kind, directory, tmp_path):
        path = generators.generate(kind, "Widget", str(tmp_path))
        assert directory in path


class TestGenerateMigration:
    def test_creates_a_timestamped_file(self, tmp_path):
        path = generators.generate_migration("create_widgets_table", str(tmp_path))
        assert os.path.basename(path).endswith("_create_widgets_table.py")

    def test_infers_the_table_from_a_create_name(self, tmp_path):
        path = generators.generate_migration("create_widgets_table", str(tmp_path))
        source = open(path, encoding="utf-8").read()
        assert 'Schema.create_table("widgets"' in source

    def test_add_to_name_produces_an_alter_migration(self, tmp_path):
        path = generators.generate_migration("add_color_to_widgets_table", str(tmp_path))
        source = open(path, encoding="utf-8").read()
        assert 'Schema.table("widgets"' in source
        assert "create_table" not in source

    def test_explicit_table_wins(self, tmp_path):
        path = generators.generate_migration("whatever", str(tmp_path), table="gadgets")
        assert 'Schema.create_table("gadgets"' in open(path, encoding="utf-8").read()

    def test_stub_has_both_directions(self, tmp_path):
        source = open(
            generators.generate_migration("create_widgets_table", str(tmp_path)),
            encoding="utf-8",
        ).read()
        assert "def up():" in source and "def down():" in source
