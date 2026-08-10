"""Translation helper: BCP 47 normalisation, fallback chain, and locales."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest

from craft.facades import DB
from craft.support.translation import __, locale_chain, normalize_locale, translate


class TestNormalizeLocale:
    @pytest.mark.parametrize(
        "given,expected",
        [
            ("en", "en"),
            ("EN", "en"),
            ("pt-BR", "pt-BR"),
            ("PT-br", "pt-BR"),
            ("pt_BR", "pt-BR"),
            ("Pt-Br", "pt-BR"),
        ],
    )
    def test_canonical_form(self, given, expected):
        # BCP 47 writes the language lowercase and the region uppercase.
        assert normalize_locale(given) == expected

    def test_none_stays_none(self):
        assert normalize_locale(None) is None
        assert normalize_locale("") is None


class TestLocaleChain:
    def test_a_regional_locale_falls_back_to_its_base(self):
        assert locale_chain("pt-BR", "en") == ["pt-BR", "pt", "en"]

    def test_a_base_locale_has_no_region_step(self):
        assert locale_chain("pt", "en") == ["pt", "en"]

    def test_the_fallback_is_not_duplicated(self):
        assert locale_chain("en", "en") == ["en"]

    def test_a_regional_fallback_expands_too(self):
        assert locale_chain("es", "pt-BR") == ["es", "pt-BR", "pt"]

    def test_casing_is_normalised_in_the_chain(self):
        assert locale_chain("PT-br", "EN") == ["pt-BR", "pt", "en"]


class TestTranslationLookup:
    @pytest.fixture(autouse=True)
    def seeded(self, migrated_database):
        DB.statement("DELETE FROM translations")
        rows = [
            ("greeting", "en", "Hello"),
            ("greeting", "pt", "Olá"),
            ("greeting", "pt-BR", "Oi"),
            ("greeting", "es", "Hola"),
            ("only_in_pt", "pt", "Apenas em pt"),
            ("only_in_en", "en", "English only"),
        ]
        for key, locale, value in rows:
            DB.statement(
                "INSERT INTO translations (key, locale, value) VALUES (?, ?, ?)",
                [key, locale, value],
            )
        yield
        DB.statement("DELETE FROM translations")

    def test_exact_locale_wins(self):
        assert __("greeting", "pt-BR") == "Oi"

    def test_each_locale_resolves_independently(self):
        assert __("greeting", "pt") == "Olá"
        assert __("greeting", "es") == "Hola"
        assert __("greeting", "en") == "Hello"

    def test_a_regional_locale_inherits_from_its_base(self):
        # Without the chain this returned the raw key.
        assert __("only_in_pt", "pt-BR") == "Apenas em pt"

    def test_a_regional_locale_falls_back_to_the_default(self):
        assert __("only_in_en", "pt-BR") == "English only"

    def test_a_missing_key_returns_the_key(self):
        assert __("no.such.key", "pt-BR") == "no.such.key"

    def test_locale_casing_does_not_matter(self):
        assert __("greeting", "PT-br") == "Oi"

    def test_placeholders_are_replaced(self):
        DB.statement(
            "INSERT INTO translations (key, locale, value) VALUES (?, ?, ?)",
            ["welcome_user", "pt-BR", "Olá, {name}!"],
        )
        assert translate("welcome_user", "pt-BR", name="Ana") == "Olá, Ana!"

    def test_placeholders_work_on_the_key_fallback(self):
        assert translate("missing_{n}", "pt-BR", n=3) == "missing_3"

    def test_config_translations_take_precedence(self, migrated_database):
        config = migrated_database.make("config")
        config.set("lang.pt-BR.greeting", "Salve")
        try:
            assert __("greeting", "pt-BR") == "Salve"
        finally:
            config.set("lang.pt-BR.greeting", None)


class TestSeededLocales:
    """The shipped catalog must carry all four locales, pt and pt-BR distinct."""

    @pytest.fixture(autouse=True)
    def seeded(self, migrated_database):
        from database.seeders.TranslationSeeder import TranslationSeeder

        TranslationSeeder(migrated_database).run()
        yield
        DB.statement("DELETE FROM translations")

    def test_all_four_locales_are_present(self):
        rows = DB.statement(
            "SELECT DISTINCT locale FROM translations", read=True
        ).fetchall()
        assert {row["locale"] for row in rows} == {"en", "pt", "pt-BR", "es"}

    def test_every_locale_has_the_same_keys(self):
        from database.seeders.TranslationSeeder import TRANSLATIONS

        base = set(TRANSLATIONS["en"])
        for locale, entries in TRANSLATIONS.items():
            assert set(entries) == base, f"{locale} has mismatched keys"

    @pytest.mark.parametrize(
        "key,european,brazilian",
        [
            ("dashboard", "Painel de Controlo", "Painel de Controle"),
            ("download", "Transferir", "Baixar"),
            ("register", "Registar", "Criar conta"),
            ("login", "Iniciar sessão", "Entrar"),
        ],
    )
    def test_portuguese_variants_are_genuinely_different(self, key, european, brazilian):
        # The seeder used to file Brazilian copy under the generic `pt` tag.
        assert __(key, "pt") == european
        assert __(key, "pt-BR") == brazilian
