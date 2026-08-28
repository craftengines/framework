"""
PublishableMixin — Status and publication helpers for Craft ORM models.
Category: Core Framework (ORM).
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from datetime import datetime, timezone
from typing import Any, Optional


class PublishableMixin:
    """Mixin for models with publication draft/published statuses."""

    status_column: str = "status"
    published_at_column: str = "published_at"

    @classmethod
    def published(cls: Any) -> Any:
        """Query scope: Filter published items."""
        return cls.query().where(getattr(cls, "status_column", "status"), "published")

    @classmethod
    def drafts(cls: Any) -> Any:
        """Query scope: Filter draft items."""
        return cls.query().where(getattr(cls, "status_column", "status"), "draft")

    @property
    def is_published(self) -> bool:
        """Return True if model instance is published."""
        status_col = getattr(self, "status_column", "status")
        return getattr(self, status_col, None) == "published"

    def publish(self, save: bool = True) -> Any:
        """Mark model instance as published."""
        status_col = getattr(self, "status_column", "status")
        pub_col = getattr(self, "published_at_column", "published_at")

        setattr(self, status_col, "published")
        if hasattr(self, "set_attribute"):
            self.set_attribute(status_col, "published")

        pub_val = datetime.now(timezone.utc).isoformat()
        setattr(self, pub_col, pub_val)
        if hasattr(self, "set_attribute"):
            self.set_attribute(pub_col, pub_val)

        if save and hasattr(self, "save"):
            self.save()
        return self

    def unpublish(self, save: bool = True) -> Any:
        """Mark model instance as draft."""
        status_col = getattr(self, "status_column", "status")
        setattr(self, status_col, "draft")
        if hasattr(self, "set_attribute"):
            self.set_attribute(status_col, "draft")

        if save and hasattr(self, "save"):
            self.save()
        return self
