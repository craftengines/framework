"""DocsController — serves the Markdown documentation as HTML.

Pages are discovered from the `documentation/` directory, so adding a guide is
a matter of dropping a `.md` file in — no navigation to update by hand.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import os
import re

from craft.exceptions import NotFoundHttpException
from craft.http import Controller, Request
from craft.support import view
from markdown_it import MarkdownIt

#: Ordered groups for the sidebar. Anything not listed lands under "More",
#: so a new file is always reachable even before it is filed here.
SECTIONS = [
    ("Getting started", ["introduction", "installation", "configuration", "cli"]),
    ("The essentials", ["container", "routing", "controllers", "views", "validation"]),
    ("Database", ["migrations", "orm"]),
    ("Features", ["security", "sessions", "cache", "queues_events", "resources", "localization"]),
    ("Going further", ["testing", "deployment"]),
]

TITLE_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


class DocsController(Controller):
    def docs_dir(self) -> str:
        from craft.facades.base import Facade

        return os.path.join(Facade._app.base_path, "documentation")

    def available(self) -> dict:
        """Map of slug -> title for every documentation page on disk."""
        directory = self.docs_dir()
        pages = {}
        if not os.path.isdir(directory):
            return pages

        for filename in sorted(os.listdir(directory)):
            if not filename.endswith(".md"):
                continue
            slug = filename[:-3]
            if slug.lower() == "readme":
                continue

            # Prefer the document's own H1 over a guess from the filename.
            try:
                with open(os.path.join(directory, filename), "r", encoding="utf-8") as handle:
                    match = TITLE_RE.search(handle.read(4096))
                title = match.group(1).strip() if match else None
            except OSError:
                title = None

            pages[slug] = title or slug.replace("_", " ").replace("-", " ").title()
        return pages

    def navigation(self, pages: dict) -> list:
        """Group the pages for the sidebar, keeping unlisted ones reachable."""
        grouped, filed = [], set()

        for heading, slugs in SECTIONS:
            items = [{"slug": s, "title": pages[s]} for s in slugs if s in pages]
            if items:
                grouped.append({"heading": heading, "items": items})
                filed.update(s for s in slugs if s in pages)

        remaining = [{"slug": s, "title": t} for s, t in pages.items() if s not in filed]
        if remaining:
            grouped.append({"heading": "More", "items": remaining})

        return grouped

    def index(self, request: Request):
        pages = self.available()
        first = "introduction" if "introduction" in pages else next(iter(pages), None)
        if first is None:
            raise NotFoundHttpException("No documentation has been published yet.")
        return self.show(request, first)

    def show(self, request: Request, page: str):
        page = os.path.basename(page)  # prevent directory traversal
        file_path = os.path.join(self.docs_dir(), f"{page}.md")

        if not os.path.exists(file_path):
            raise NotFoundHttpException(f"Documentation page '{page}' not found.")

        with open(file_path, "r", encoding="utf-8") as handle:
            content = handle.read()

        pages = self.available()
        return view("docs.show", {
            "content": MarkdownIt().render(content),
            "current_page": page,
            "page_title": pages.get(page, page),
            "navigation": self.navigation(pages),
        })
