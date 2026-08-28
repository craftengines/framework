"""BlogPost Model."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.orm import Model, SluggableMixin, PublishableMixin, BelongsTo, HasMany, BelongsToMany


class BlogPost(Model, SluggableMixin, PublishableMixin):
    __table__ = "blog_posts"

    fillable = [
        "user_id",
        "category_id",
        "title",
        "slug",
        "excerpt",
        "content",
        "status",
        "published_at",
    ]
    slug_source_column = "title"
    slug_target_column = "slug"

    def category(self) -> BelongsTo:
        from app.Models.BlogCategory import BlogCategory
        return self.belongs_to(BlogCategory, foreign_key="category_id")

    def comments(self) -> HasMany:
        from app.Models.BlogComment import BlogComment
        return self.has_many(BlogComment, foreign_key="post_id")

    def tags(self) -> BelongsToMany:
        from app.Models.BlogTag import BlogTag
        return self.belongs_to_many(
            BlogTag, table="blog_post_tag", foreign_key="post_id", related_key="tag_id"
        )
