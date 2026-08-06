"""
DocsController — Dynamically loads, parses, and serves Markdown documentation.
Category: Controller (HTTP Presentation Layer).
Relations:
  - Interacts with public markdown pages in the `/documentation` directory.
  - Renders HTML payload using [docs/show.blade.py](file:///d:/data/www/codepy/resources/views/docs/show.blade.py).
References:
  - Documentation: [documentation/routing.md](file:///d:/data/www/codepy/documentation/routing.md)
  - Skill: `codepy-development` ([SKILL.md](file:///d:/data/www/codepy/.agents/skills/codepy-development/SKILL.md))
"""
# Codepy Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import os
from codepy.http import Controller, Request
from codepy.support import view
from codepy.exceptions import NotFoundHttpException
from markdown_it import MarkdownIt

class DocsController(Controller):
    def index(self, request: Request):
        return self.show(request, "introduction")

    def show(self, request: Request, page: str):
        # Prevent directory traversal
        page = os.path.basename(page)
        
        # Read from documentation folder
        from codepy.facades.base import Facade
        docs_dir = os.path.join(Facade._app.base_path, "documentation")
        file_path = os.path.join(docs_dir, f"{page}.md")
        
        if not os.path.exists(file_path):
            raise NotFoundHttpException(f"Documentation page '{page}' not found.")
            
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        md = MarkdownIt()
        html_content = md.render(content)
        
        return view("docs.show", {
            "content": html_content,
            "current_page": page,
        })
