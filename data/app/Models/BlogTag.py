"""BlogTag Model."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.orm import Model, SluggableMixin, BelongsToMany


class BlogTag(Model, SluggableMixin):
    __table__ = "blog_tags"

    fillable = ["name", "slug"]
    slug_source_column = "name"
    slug_target_column = "slug"

    def posts(self) -> BelongsToMany:
        from app.Models.BlogPost import BlogPost
        return self.belongs_to_many(
            BlogPost, table="blog_post_tag", foreign_key="tag_id", related_key="post_id"
        )
