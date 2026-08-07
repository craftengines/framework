"""Base Controller class for Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from typing import Any, Dict, Optional
from services.http.response import JsonResponse, Response, redirect


class Controller:
    """Base Controller providing helper methods for views, responses, and authorization."""

    def view(self, template_name: str, data: Optional[Dict[str, Any]] = None) -> Response:
        """Render a template.

        Errors propagate to the exception handler. Swallowing them here — as
        this used to — turned a broken template into a page that looked fine,
        which is far harder to debug than a 500.
        """
        from services.container.application import Container

        forge = Container.getInstance().make("view")
        return Response(forge.render(template_name, data or {}))

    def json(self, data: Any, status: int = 200) -> JsonResponse:
        return JsonResponse(data, status=status)

    def redirect(self, url: str = "", route: Optional[str] = None, **kwargs) -> Any:
        return redirect(url=url, route=route, **kwargs)

    def no_content(self) -> Response:
        return Response("", status=204)
