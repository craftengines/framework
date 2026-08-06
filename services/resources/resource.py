"""API Resource implementation for Codepy Framework."""

from typing import Any, Dict
from services.http.response import JsonResponse


class Resource:
    def __init__(self, resource: Any):
        self.resource = resource

    def to_array(self, request=None) -> Dict[str, Any]:
        if hasattr(self.resource, "to_dict"):
            return self.resource.to_dict()
        if isinstance(self.resource, dict):
            return self.resource
        return {}

    def response(self, status: int = 200) -> JsonResponse:
        return JsonResponse(self.to_array(), status=status)
