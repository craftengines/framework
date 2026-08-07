"""Post controller — demonstrates CRUD with models, validation, and resources under Blog directory."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.facades import Auth, Gate
from craft.http.controller import Controller
from craft.http.response import JsonResponse, Response, redirect
from app.Models.Post import Post
from app.Http.Requests.StorePostRequest import StorePostRequest
from app.Http.Resources.PostResource import PostResource


class PostController(Controller):
    """Write actions require an authenticated user and go through
    `PostPolicy` via `Gate.authorize` — route middleware alone is not
    enough here since ownership (not just login) gates update/delete."""

    def index(self, request):
        posts = Post.query().order_by_desc("created_at").paginate(15)
        if request.expects_json():
            # Convert each post to a resource dict for JSON serialization
            return JsonResponse([PostResource(p).to_array() for p in posts])
        return self.view("posts.index", {"posts": posts})

    def create(self, request):
        return self.view("posts.create", {"show_sidebar": True})

    def store(self, request):
        user = Auth.user()
        Gate.authorize("create", user)
        form = StorePostRequest(request)
        data = form.validated()
        data["user_id"] = user.get_attribute("id")

        post = Post.create(data)
        if request.expects_json():
            return PostResource(post).response(status=201)
        return redirect(route="posts.index")

    def show(self, request, posts):
        post = Post.query().where("id", posts).first()
        if not post:
            return Response("Not found", 404)
        if request.expects_json():
            return PostResource(post)
        return self.view("posts.show", {"post": post})

    def edit(self, request, posts):
        post = Post.query().where("id", posts).first()
        if not post:
            return Response("Not found", 404)
        Gate.authorize("update", Auth.user(), post)
        return self.view("posts.edit", {"post": post, "show_sidebar": True})

    def update(self, request, posts):
        post = Post.query().where("id", posts).first()
        if not post:
            return Response("Not found", 404)
        Gate.authorize("update", Auth.user(), post)
        form = StorePostRequest(request)
        post.update_attributes(form.validated())
        if request.expects_json():
            return PostResource(post)
        return redirect(route="posts.index")

    def destroy(self, request, posts):
        post = Post.query().where("id", posts).first()
        if not post:
            return Response("Not found", 404) if not request.expects_json() else self.no_content()
        Gate.authorize("delete", Auth.user(), post)
        post.delete()
        if request.expects_json():
            return self.no_content()
        return redirect(route="posts.index")
