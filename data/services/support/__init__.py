"""Support package exports."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from services.support.collection import Collection
from services.support.translation import __, translate, locale_chain, normalize_locale
from services.http.response import Response, JsonResponse, redirect


def view(template_name: str, data: dict = None) -> Response:
    from services.container.application import Container
    app = Container.getInstance()
    try:
        forge = app.make("view")
        html = forge.render(template_name, data or {})
        return Response(html)
    except Exception:
        return Response(f"View {template_name} rendered")
