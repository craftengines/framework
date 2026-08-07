"""API routes — JSON API endpoints."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.facades import Route
from app.Http.Controllers.Blog.PostController import PostController
from app.Http.Resources.PostResource import PostResource


Route.group(
    lambda: (
        Route.api_resource("posts", PostController),
    ),
    prefix="/api/v1",
    name="api.",
)
