"""Test Blog Feature & DX Accelerator Mixins (SluggableMixin, PublishableMixin)."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest
from craft.facades import Route
from engine.orm.sluggable import slugify
from app.Models.BlogCategory import BlogCategory
from app.Models.BlogPost import BlogPost
from app.Models.BlogComment import BlogComment
from starlette.testclient import TestClient


def test_slugify_helper():
    """Verify slugify function handles special characters, accents, and spacing."""
    assert slugify("Hello World") == "hello-world"
    assert slugify("Craft Engine: AI Accelerator 2026!") == "craft-engine-ai-accelerator-2026"
    assert slugify("Açção & Integração") == "accao-integracao"
    assert slugify("") == ""


def test_sluggable_mixin_generate_slug(migrated_database):
    """Verify SluggableMixin generates unique slugs."""
    cat1 = BlogCategory({"name": "AI & Engineering"})
    cat1.generate_slug()
    cat1.save()
    assert cat1.slug == "ai-engineering"

    # Duplicate title must get auto-increment suffix
    cat2 = BlogCategory({"name": "AI & Engineering"})
    cat2.generate_slug()
    cat2.save()
    assert cat2.slug == "ai-engineering-1"

    found = BlogCategory.find_by_slug("ai-engineering")
    assert found is not None
    assert found.id == cat1.id


def test_publishable_mixin_scopes(migrated_database):
    """Verify PublishableMixin handles status and query scopes."""
    post1 = BlogPost({
        "title": "First Craft Article",
        "content": "Craft Engine rules.",
        "status": "draft",
    })
    post1.generate_slug()
    post1.save()

    assert not post1.is_published
    assert len(BlogPost.published().get()) == 0
    assert len(BlogPost.drafts().get()) == 1

    post1.publish()
    assert post1.is_published
    assert len(BlogPost.published().get()) == 1
    assert len(BlogPost.drafts().get()) == 0


def test_blog_accelerator_http_routes(migrated_database):
    """Verify public blog HTTP endpoints with TestClient."""
    from bootstrap.app import asgi_app

    client = TestClient(asgi_app)

    # Seed a published blog post
    category = BlogCategory({"name": "Tutorials"})
    category.generate_slug()
    category.save()

    post = BlogPost({
        "category_id": category.id,
        "title": "Getting Started with Craft Engine",
        "content": "Full stack Python simplified.",
        "status": "published",
    })
    post.generate_slug()
    post.save()

    # Test Blog Index JSON response
    res = client.get("/api/v1/blog", headers={"Accept": "application/json"})
    assert res.status_code == 200
    data = res.json()
    assert len(data["posts"]) >= 1
    assert data["posts"][0]["title"] == "Getting Started with Craft Engine"

    # Test Blog Single Post by Slug
    res = client.get(f"/api/v1/blog/{post.slug}", headers={"Accept": "application/json"})
    assert res.status_code == 200
    assert res.json()["slug"] == "getting-started-with-craft-engine"

    # Test Submitting Comment
    res = client.post(
        f"/api/v1/blog/{post.slug}/comments",
        json={"author_name": "Dev Agent", "author_email": "agent@craft.local", "content": "Awesome architecture!"},
        headers={"Accept": "application/json"}
    )
    assert res.status_code == 201
    assert res.json()["message"] == "Comment submitted"
