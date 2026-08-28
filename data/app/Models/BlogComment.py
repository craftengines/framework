"""BlogComment Model."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.orm import Model, BelongsTo


class BlogComment(Model):
    __table__ = "blog_comments"

    fillable = ["post_id", "author_name", "author_email", "content", "status"]

    def post(self) -> BelongsTo:
        from app.Models.BlogPost import BlogPost
        return self.belongs_to(BlogPost, foreign_key="post_id")
