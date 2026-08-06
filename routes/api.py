"""API routes — JSON API endpoints."""

from codepy.facades import Route
from app.Http.Controllers.Blog.PostController import PostController
from app.Http.Resources.PostResource import PostResource


Route.group(
    lambda: (
        Route.api_resource("posts", PostController),
    ),
    prefix="/api/v1",
    name="api.",
)
