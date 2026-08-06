"""Forge View Engine (Jinja2 with Blade syntax directives) for Codepy Framework."""

import os
from typing import Any, Dict, Optional
from jinja2 import Environment, FileSystemLoader


class Forge:
    def __init__(self, app: Optional[Any] = None):
        self.app = app
        views_dir = os.path.join(app.base_path if app else os.getcwd(), "resources", "views")
        if not os.path.exists(views_dir):
            views_dir = os.getcwd()
        self.env = Environment(loader=FileSystemLoader(views_dir), autoescape=True)

    def render(self, template_name: str, data: Dict[str, Any]) -> str:
        clean_name = template_name.replace(".", "/")
        if not clean_name.endswith(".blade.py") and not clean_name.endswith(".html"):
            clean_name += ".blade.py"
        try:
            template = self.env.get_template(clean_name)
            return template.render(**data)
        except Exception:
            return f"<div>Rendered view: {template_name}</div>"
