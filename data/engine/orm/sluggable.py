"""
SluggableMixin — Automatic URL-safe slug generation for Craft ORM models.
Category: Core Framework (ORM).
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import re
import unicodedata
from typing import Any, Optional


def slugify(value: str) -> str:
    """Convert string to URL-safe hyphenated slug."""
    if not value:
        return ""
    value = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value.lower()).strip()
    return re.sub(r"[-\s]+", "-", value)


class SluggableMixin:
    """Mixin for models requiring URL slug attributes."""

    slug_source_column: str = "title"
    slug_target_column: str = "slug"

    @classmethod
    def find_by_slug(cls: Any, slug: str) -> Optional[Any]:
        """Find model instance by slug."""
        target_col = getattr(cls, "slug_target_column", "slug")
        return cls.query().where(target_col, slug).first()

    @classmethod
    def find_by_slug_or_fail(cls: Any, slug: str) -> Any:
        """Find model instance by slug or raise ValueError."""
        instance = cls.find_by_slug(slug)
        if not instance:
            raise ValueError(f"{cls.__name__} with slug '{slug}' not found.")
        return instance

    def generate_slug(self, force: bool = False) -> str:
        """Generate unique slug for model instance."""
        target_col = getattr(self, "slug_target_column", "slug")
        source_col = getattr(self, "slug_source_column", "title")

        if not force and getattr(self, target_col, None):
            return getattr(self, target_col)

        raw_val = getattr(self, source_col, None)
        if not raw_val and hasattr(self, "name"):
            raw_val = self.name

        base_slug = slugify(raw_val or "untitled")
        slug = base_slug
        counter = 1

        while True:
            q = self.__class__.query()
            if getattr(self, "id", None):
                q = q.where("id", "!=", self.id)
            if not q.where(target_col, slug).exists():
                break
            slug = f"{base_slug}-{counter}"
            counter += 1

        setattr(self, target_col, slug)
        if hasattr(self, "set_attribute"):
            self.set_attribute(target_col, slug)
        elif hasattr(self, "_attributes") and isinstance(self._attributes, dict):
            self._attributes[target_col] = slug
        return slug
