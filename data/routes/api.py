"""API routes — JSON API endpoints."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.facades import Route
from app.Http.Controllers.Blog.PostController import PostController
from app.Http.Resources.PostResource import PostResource


Route.group(
    lambda: (
        # Reads stay public; writes require a valid API token (the
        # controller additionally checks ownership via PostPolicy/Gate).
        Route.api_resource("posts", PostController, write_middleware="api"),
    ),
    prefix="/api/v1",
    name="api.",
)
