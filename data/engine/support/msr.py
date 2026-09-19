"""MSR JSON manifest builder: the application describes itself to registries.

MSR JSON (https://msrjson.org) is an open metadata protocol for software. A
product publishes one manifest at `https://<domain>/.well-known/msr.json`, and
software registries, package managers and AI agents read it instead of
scraping a product page. Every Craft application ships the endpoint natively.

The manifest is assembled from three sources, never invented:

- `config/msr.py` for what only the owner knows (type, license, vendor, pricing);
- `pyproject.toml` and `CHANGELOG.md` for the release (version and date);
- the translation store for the descriptions, one entry per configured locale.

A field whose value is unknown is omitted. A required field that cannot be
resolved raises `ManifestIncompleteError`, and the endpoint answers 404 rather
than publish a manifest a registry would act on wrongly.

Category: Core Framework (Support).
Relations:
  - Served by `engine/http/msr.py`, mounted by `engine/http/kernel.py`.
  - Printed and validated by `dev msr:show` / `dev msr:validate` (`engine/cli/app.py`).
References:
  - Guide: `documentation/msr.md`
  - Protocol: https://github.com/msrjson/specification
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import re
import tomllib
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

#: The canonical schema URL; it is the `$schema` value and the schema's `$id`.
SCHEMA_URL = "https://msrjson.org/schemas/msr-2.0.json"
#: Where the protocol requires the manifest to be served.
MANIFEST_PATH = "/.well-known/msr.json"
#: Constant for every MSR JSON 2.0 manifest; only `canonical_url` is added per product.
PROTOCOL = {
    "name": "MSR JSON",
    "version": "2.0.0",
    "author": "Antonio Santos",
    "specification_license": "CC-BY-4.0",
    "reference_implementation_license": "MIT",
}
#: Description fields, each resolved from the key `msr.entity.<field>`.
DESCRIPTION_FIELDS = ("tagline", "summary", "text")

_DOMAIN = re.compile(r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$")
_NON_SLUG = re.compile(r"[^a-z0-9]+")

#: Resolves `(key, locale)` to text, returning the key itself when it is missing.
Translator = Callable[[str, str], str]


class ManifestIncompleteError(Exception):
    """Raised when a field the protocol requires cannot be resolved."""

    code = "MSR_MANIFEST_INCOMPLETE"

    def __init__(self, field: str) -> None:
        """Store the unresolved field.

        Args:
            field: The manifest path of the missing value, e.g. `entity.domain`.
        """
        super().__init__(f"{self.code}: {field}")
        self.field = field


class ManifestBuilder:
    """Assembles the MSR JSON manifest of one application."""

    def __init__(self, settings: Mapping[str, Any], base_path: Path, translator: Translator) -> None:
        """Bind the builder to its sources.

        Args:
            settings: The `msr` configuration section (upper-case keys).
            base_path: The application root holding `pyproject.toml` and `CHANGELOG.md`.
            translator: Resolves the description keys per locale.
        """
        self.settings = settings
        self.base_path = base_path
        self.translator = translator

    def build(self) -> dict[str, Any]:
        """Return the manifest as a JSON-ready mapping.

        Returns:
            The manifest, with every unknown optional field omitted.

        Raises:
            ManifestIncompleteError: If a required field cannot be resolved.
        """
        domain = self._domain()
        return prune({
            "$schema": SCHEMA_URL,
            "protocol": {**PROTOCOL, "canonical_url": f"https://{domain}{MANIFEST_PATH}"},
            "entity": self._entity(domain),
            "capabilities": self._capabilities(),
            "releases": {"latest": self._release()},
        })

    def _setting(self, name: str) -> Any:
        return self.settings.get(name)

    def _domain(self) -> str:
        domain = str(self._setting("DOMAIN") or urlsplit(str(self._setting("URL") or "")).hostname or "")
        if not _DOMAIN.match(domain.lower()):
            raise ManifestIncompleteError("entity.domain")
        return domain.lower()

    def _entity(self, domain: str) -> dict[str, Any]:
        name = str(self._setting("NAME") or "").strip()
        if not name:
            raise ManifestIncompleteError("entity.name")
        vendor = dict(self._setting("VENDOR") or {})
        return {
            "name": name,
            "slug": str(self._setting("SLUG") or "") or slugify(name),
            "domain": domain,
            "type": self._required("TYPE", "entity.type"),
            "license": dict(self._setting("LICENSE") or {}),
            "vendor": {**vendor, "website": vendor.get("website") or self._setting("URL")} if vendor.get("name") else None,
            "descriptions": self._descriptions(),
        }

    def _descriptions(self) -> dict[str, dict[str, str]]:
        descriptions = {}
        for locale in self._setting("LOCALES") or ():
            fields = {field: self._describe(field, str(locale)) for field in DESCRIPTION_FIELDS}
            if fields["summary"]:
                descriptions[str(locale)] = {k: v for k, v in fields.items() if v}
        if not descriptions:
            raise ManifestIncompleteError("entity.descriptions")
        return descriptions

    def _describe(self, field: str, locale: str) -> str | None:
        key = f"msr.entity.{field}"
        value = self.translator(key, locale)
        return value if value and value != key else None

    def _capabilities(self) -> dict[str, Any]:
        deployment = list(self._setting("DEPLOYMENT") or ())
        if not deployment:
            raise ManifestIncompleteError("capabilities.deployment")
        return {
            "deployment": deployment,
            "pricing": dict(self._setting("PRICING") or {}),
            "integrations": list(self._setting("INTEGRATIONS") or ()),
        }

    def _release(self) -> dict[str, Any]:
        version = self._setting("VERSION") or read_project_version(self.base_path)
        if not version:
            raise ManifestIncompleteError("releases.latest.version")
        published_at = self._setting("PUBLISHED_AT") or read_release_date(self.base_path, str(version))
        if not published_at:
            raise ManifestIncompleteError("releases.latest.published_at")
        return {
            "version": str(version),
            "published_at": str(published_at),
            "release_type": self._setting("RELEASE_TYPE"),
            "changelog_url": self._setting("CHANGELOG_URL"),
        }

    def _required(self, name: str, field: str) -> str:
        value = self._setting(name)
        if not value:
            raise ManifestIncompleteError(field)
        return str(value)


def slugify(name: str) -> str:
    """Return the lowercase kebab-case slug the protocol requires.

    Args:
        name: The product name.

    Returns:
        The slug, e.g. `Craft Engine` -> `craft-engine`.
    """
    return _NON_SLUG.sub("-", name.lower()).strip("-")


def read_project_version(base_path: Path) -> str | None:
    """Return `[project].version` from the application's `pyproject.toml`.

    Args:
        base_path: The application root.

    Returns:
        The version, or None when the file or the field is absent.
    """
    path = base_path / "pyproject.toml"
    if not path.is_file():
        return None
    version = tomllib.loads(path.read_text()).get("project", {}).get("version")
    return str(version) if version else None


def read_release_date(base_path: Path, version: str) -> str | None:
    """Return the release date of `version` from `CHANGELOG.md` as RFC 3339.

    Reads the Keep a Changelog heading, e.g. `## [3.21.0] r00014 - 2026-09-16`.

    Args:
        base_path: The application root.
        version: The released version to look up.

    Returns:
        `YYYY-MM-DDT00:00:00Z`, or None when the version has no dated heading.
    """
    path = base_path / "CHANGELOG.md"
    if not path.is_file():
        return None
    heading = re.compile(rf"^## \[{re.escape(version)}\][^\n]*?(\d{{4}}-\d{{2}}-\d{{2}})\s*$", re.MULTILINE)
    match = heading.search(path.read_text())
    return f"{match.group(1)}T00:00:00Z" if match else None


def validate_manifest(manifest: Mapping[str, Any], schema_url: str = SCHEMA_URL) -> list[str]:
    """Validate a manifest against the canonical schema, fetched over HTTPS.

    Args:
        manifest: The manifest mapping.
        schema_url: Where the schema is published.

    Returns:
        One `path -> message` line per violation; empty when valid.

    Raises:
        ModuleNotFoundError: If `jsonschema` is not installed (`pip install craft[msr]`).
        urllib.error.URLError: If the schema cannot be fetched.
    """
    import json
    import urllib.request

    from jsonschema import Draft202012Validator

    # An explicit agent: the schema host refuses the default `Python-urllib` one.
    request = urllib.request.Request(schema_url, headers={"User-Agent": "craft-engine-msr/1.0"})
    with urllib.request.urlopen(request, timeout=15) as response:  # noqa: S310 - fixed https URL
        schema = json.load(response)
    errors = sorted(Draft202012Validator(schema).iter_errors(manifest), key=lambda e: list(e.path))
    return [f"{'/'.join(map(str, e.path)) or '(root)'} -> {e.message}" for e in errors]


def prune(value: Any) -> Any:
    """Drop None and empty containers recursively; the schema rejects nulls.

    Args:
        value: A JSON-ready value.

    Returns:
        A new value without empty optional fields; the input is not modified.
    """
    if isinstance(value, dict):
        cleaned = {k: prune(v) for k, v in value.items()}
        return {k: v for k, v in cleaned.items() if v not in (None, {}, [], "")}
    if isinstance(value, list):
        return [prune(v) for v in value]
    return value


__all__ = [
    "DESCRIPTION_FIELDS",
    "MANIFEST_PATH",
    "PROTOCOL",
    "SCHEMA_URL",
    "ManifestBuilder",
    "ManifestIncompleteError",
    "prune",
    "read_project_version",
    "read_release_date",
    "slugify",
    "validate_manifest",
]
