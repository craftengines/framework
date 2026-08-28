# DX Acceleration & Domain Scaffolding Guide

Craft Engine is built for maximum developer ergonomics and rapid feature delivery. Both **AI Agents** and **Senior Developers** can leverage Craft Engine's ORM Mixins, Query Scopes, and Facades to implement complex business domains in record time.

---

## 1. ORM Mixins (`engine/orm/`)

### SluggableMixin
Automatically generates unique, URL-safe slugs for models from `title`, `name`, or a designated source column.

```python
from craft.orm import Model, SluggableMixin

class BlogPost(Model, SluggableMixin):
    __table__ = "blog_posts"
    fillable = ["title", "slug", "content"]
    
    slug_source_column = "title"   # Default source column
    slug_target_column = "slug"    # Default target column

# Usage:
post = BlogPost({"title": "Getting Started with Craft Engine"})
post.generate_slug() # -> "getting-started-with-craft-engine"
post.save()

# Querying by slug:
post = BlogPost.find_by_slug("getting-started-with-craft-engine")
```

### PublishableMixin
Provides draft/published status lifecycle management, timestamping (`published_at`), and built-in query scopes.

```python
from craft.orm import Model, PublishableMixin

class BlogPost(Model, PublishableMixin):
    __table__ = "blog_posts"
    fillable = ["title", "status", "published_at"]

# Built-in Scopes:
published_posts = BlogPost.published().get()
draft_posts = BlogPost.drafts().get()

# Model instance lifecycle helpers:
post.publish()    # Sets status = 'published', fills published_at timestamp, saves
post.unpublish()  # Sets status = 'draft', saves
if post.is_published:
    ...
```

---

## 2. Speeding Up Business Logic

By combining `SluggableMixin` and `PublishableMixin` with Craft ORM relations, AI agents and developers write concise, declarative controllers:

```python
from craft.http.controller import Controller
from craft.http.response import JsonResponse
from app.Models.BlogPost import BlogPost

class BlogController(Controller):
    def index(self, request):
        return JsonResponse([
            p.to_dict() for p in BlogPost.published().order_by_desc("created_at").get()
        ])

    def show(self, request, slug):
        post = BlogPost.find_by_slug(slug)
        if not post or not post.is_published:
            return self.not_found("Article not found")
        return JsonResponse(post.to_dict())
```

---

## 3. Best Practices for AI Agents & Senior Engineers

1. **Inherit Mixins First**: Always inherit ORM mixins alongside `Model` (`class Post(Model, SluggableMixin, PublishableMixin)`).
2. **Use Query Scopes over Manual Filters**: Prefer `BlogPost.published()` over manual `where("status", "published")`.
3. **Use Facades & Active Record**: Leverage `Route`, `DB`, `Auth`, `Gate`, `Cache` for clean, expressive controllers.
