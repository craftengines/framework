"""Media Model for Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import json
from typing import Any, Dict

from craft.orm.model import Model


class Media(Model):
    __table__ = "media"

    fillable = [
        "model_type",
        "model_id",
        "collection_name",
        "disk",
        "filename",
        "mime_type",
        "size",
        "width",
        "height",
        "conversions",
    ]

    def get_conversions(self) -> Dict[str, Any]:
        """Return parsed conversions dictionary."""
        val = getattr(self, "conversions", None)
        if isinstance(val, dict):
            return val
        if val and isinstance(val, str):
            try:
                return json.loads(val)
            except Exception:
                return {}
        return {}

    def set_conversions(self, conversions: Dict[str, Any]) -> None:
        """Serialize conversions dictionary to JSON string."""
        self.conversions = json.dumps(conversions)
