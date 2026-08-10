"""API Resources for Craft Framework.

A Resource controls exactly what leaves the application for a given model.
Override either `to_array()` or `to_dict()` — whichever reads better; both are
honoured::

    class PostResource(Resource):
        def to_array(self, request=None):
            return {"id": self.resource.get_attribute("id")}

Category: Core Framework (Resources).
Relations:
  - Subclassed by `app/Http/Resources/*`; wraps a Model or a Collection for
    `.response()`; independent of `Model.hidden` — it is an explicit allow-list.
References:
  - Guide: `documentation/resources.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from engine.http.response import JsonResponse


class Resource:
    """Transforms a single model into its public representation."""

    def __init__(self, resource: Any):
        self.resource = resource

    # -- default representation ------------------------------------------------

    def _default_array(self) -> Dict[str, Any]:
        """Fallback when the subclass declares no transformation."""
        if isinstance(self.resource, dict):
            return dict(self.resource)
        if hasattr(self.resource, "to_dict"):
            return self.resource.to_dict()
        return {}

    # -- transformation hooks --------------------------------------------------

    def to_array(self, request: Any = None) -> Dict[str, Any]:
        """The public representation.

        If the subclass overrode `to_dict()` instead, that wins. The base class
        used to read `self.resource.to_dict()` directly, so a subclass that
        defined `to_dict()` — which is what `craft make:resource` generates —
        was silently ignored and the entire model was emitted instead.
        """
        if type(self).to_dict is not Resource.to_dict:
            return self.to_dict()
        return self._default_array()

    def to_dict(self) -> Dict[str, Any]:
        if type(self).to_array is not Resource.to_array:
            return self.to_array()
        return self._default_array()

    # -- helpers ---------------------------------------------------------------

    def when(self, condition: Any, value: Any, default: Any = None) -> Any:
        """Include a value only when `condition` holds."""
        return value() if (condition and callable(value)) else (value if condition else default)

    def response(self, status: int = 200, request: Any = None) -> JsonResponse:
        return JsonResponse(self.to_array(request), status=status)

    @classmethod
    def collection(cls, items: Iterable[Any]) -> "ResourceCollection":
        return ResourceCollection(cls, items)

    @classmethod
    def make(cls, resource: Any) -> "Resource":
        return cls(resource)

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.to_array()!r}>"


class ResourceCollection:
    """Applies a Resource to every item of a collection."""

    def __init__(self, resource_class: type, items: Iterable[Any]):
        self.resource_class = resource_class
        # Keep the original around: a paginated Collection carries `pagination`
        # metadata that a plain list() would drop.
        self.source = items
        self.items = list(items or [])

    def to_array(self, request: Any = None) -> List[Dict[str, Any]]:
        return [self.resource_class(item).to_array(request) for item in self.items]

    def to_dict(self) -> List[Dict[str, Any]]:
        return self.to_array()

    def response(self, status: int = 200, meta: Optional[Dict[str, Any]] = None) -> JsonResponse:
        payload: Dict[str, Any] = {"data": self.to_array()}
        pagination = getattr(self.source, "pagination", None)
        if pagination:
            payload["meta"] = pagination
        if meta:
            payload.setdefault("meta", {}).update(meta)
        return JsonResponse(payload, status=status)

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self):
        return iter(self.to_array())


__all__ = ["Resource", "ResourceCollection"]
