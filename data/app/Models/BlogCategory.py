"""BlogCategory Model."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.orm import Model, SluggableMixin, HasMany


class BlogCategory(Model, SluggableMixin):
    __table__ = "blog_categories"

    fillable = ["name", "slug", "description"]
    slug_source_column = "name"
    slug_target_column = "slug"

    def posts(self) -> HasMany:
        from app.Models.BlogPost import BlogPost
        return self.has_many(BlogPost, foreign_key="category_id")
