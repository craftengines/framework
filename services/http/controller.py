"""Base Controller class for Codepy Framework."""

from typing import Any, Dict, Optional
from services.http.response import JsonResponse, Response, redirect


class Controller:
    """Base Controller providing helper methods for views, responses, and authorization."""

    def view(self, template_name: str, data: Optional[Dict[str, Any]] = None) -> Response:
        from services.container.application import Container
        app = Container.getInstance()
        try:
            forge = app.make("view")
            html = forge.render(template_name, data or {})
            return Response(html)
        except Exception:
            # Fallback inline view render if view engine is not yet booted
            return Response(f"View [{template_name}] rendered")

    def json(self, data: Any, status: int = 200) -> JsonResponse:
        return JsonResponse(data, status=status)

    def redirect(self, url: str = "", route: Optional[str] = None, **kwargs) -> Any:
        return redirect(url=url, route=route, **kwargs)

    def no_content(self) -> Response:
        return Response("", status=204)
