"""BlogAcceleratorController — Public blog controller leveraging Craft DX Accelerators."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.http.controller import Controller
from craft.http.response import JsonResponse, Response, redirect
from app.Models.BlogPost import BlogPost
from app.Models.BlogCategory import BlogCategory
from app.Models.BlogComment import BlogComment


class BlogAcceleratorController(Controller):
    """Demonstrates high-velocity Blog domain actions for AI agents & Senior Devs."""

    def index(self, request):
        """Published posts feed."""
        posts = BlogPost.published().order_by_desc("created_at").get()
        categories = BlogCategory.query().get()

        if request.expects_json():
            return JsonResponse({
                "posts": [p.to_dict() for p in posts],
                "categories": [c.to_dict() for c in categories]
            })

        return self.view("blog.index", {
            "posts": posts,
            "categories": categories,
        })

    def show(self, request, slug):
        """View a single post by slug using SluggableMixin & PublishableMixin."""
        post = BlogPost.find_by_slug(slug)
        if not post or not post.is_published:
            return Response("Post not found", 404)

        comments = post.comments().where("status", "approved").get()

        if request.expects_json():
            data = post.to_dict()
            data["comments"] = [c.to_dict() for c in comments]
            return JsonResponse(data)

        return self.view("blog.show", {
            "post": post,
            "comments": comments,
        })

    def category(self, request, slug):
        """View posts by category slug."""
        category = BlogCategory.find_by_slug(slug)
        if not category:
            return Response("Category not found", 404)

        posts = category.posts().where("status", "published").get()

        if request.expects_json():
            return JsonResponse({
                "category": category.to_dict(),
                "posts": [p.to_dict() for p in posts]
            })

        return self.view("blog.index", {
            "category": category,
            "posts": posts,
        })

    def comment(self, request, slug):
        """Add a comment to a published blog post."""
        post = BlogPost.find_by_slug(slug)
        if not post or not post.is_published:
            return Response("Post not found", 404)

        author_name = request.input("author_name", "Anonymous")
        author_email = request.input("author_email", "")
        content = request.input("content", "").strip()

        if not content:
            if request.expects_json():
                return JsonResponse({"error": "Comment content cannot be empty"}, status=422)
            return Response("Content cannot be empty", 400)

        comment = BlogComment.create({
            "post_id": post.id,
            "author_name": author_name,
            "author_email": author_email,
            "content": content,
            "status": "approved"
        })

        if request.expects_json():
            return JsonResponse({"message": "Comment submitted", "comment": comment.to_dict()}, status=201)

        return redirect(route="blog.show", slug=slug)
