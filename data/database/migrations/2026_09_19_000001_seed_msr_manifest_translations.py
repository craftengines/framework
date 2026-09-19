"""Migration: the translation keys that describe the application in its MSR JSON manifest.

`/.well-known/msr.json` publishes `entity.descriptions` from the keys
`msr.entity.*`, one set per locale. `TranslationSeeder` carries them for fresh
databases, but it rewrites the whole table; an existing database gets them
here instead, inserted only where the key and locale are absent, so copy an
operator already edited is never overwritten.

Category: Framework data (i18n).
References:
  - Guide: `documentation/msr.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.facades import DB
from database.seeders.TranslationSeeder import TRANSLATIONS

PREFIX = "msr."


def up():
    for locale, entries in TRANSLATIONS.items():
        for key, value in entries.items():
            if key.startswith(PREFIX) and not _exists(key, locale):
                DB.statement(
                    "INSERT INTO translations (key, locale, value) VALUES (?, ?, ?)",
                    [key, locale, value],
                )


def down():
    # Forward-only data: the rows may have been edited by an operator since,
    # and a rollback must not destroy that copy (NR-02).
    pass


def _exists(key, locale):
    row = DB.statement(
        "SELECT 1 FROM translations WHERE key = ? AND locale = ?", [key, locale], read=True
    ).fetchone()
    return row is not None
