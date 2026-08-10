"""Eager loading — `with_()` must collapse N+1 into a fixed number of queries.

These tests count the SQL actually issued. Asserting on results alone would pass
just as happily with lazy loading, which is the bug being prevented.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest

from craft.facades import DB
from craft.orm.exceptions import RelationNotFoundError
from craft.orm.model import Model


class Comment(Model):
    __table__ = "el_comments"
    fillable = ["body", "post_id"]

    def post(self):
        return self.belongs_to(Post, foreign_key="post_id")


class Post(Model):
    __table__ = "el_posts"
    fillable = ["title", "author_id"]

    def author(self):
        return self.belongs_to(Author, foreign_key="author_id")

    def comments(self):
        return self.has_many(Comment, foreign_key="post_id")


class Author(Model):
    __table__ = "el_authors"
    fillable = ["name"]

    def posts(self):
        return self.has_many(Post, foreign_key="author_id")

    def latest_post(self):
        return self.has_one(Post, foreign_key="author_id")

    def tags(self):
        return self.belongs_to_many(
            Tag,
            pivot_table="el_author_tag",
            foreign_pivot_key="author_id",
            related_pivot_key="tag_id",
        )


class Tag(Model):
    __table__ = "el_tags"
    fillable = ["label"]


class QueryCounter:
    """Wraps the DatabaseManager to count SELECTs issued."""

    def __init__(self, db):
        self.db = db
        self.queries = []
        self._original = db.statement

    def __enter__(self):
        def counting(query, bindings=None, read=False):
            if query.lstrip().upper().startswith("SELECT"):
                self.queries.append(query)
            return self._original(query, bindings, read)

        self.db.statement = counting
        return self

    def __exit__(self, *exc):
        self.db.statement = self._original
        return False

    @property
    def count(self) -> int:
        return len(self.queries)


@pytest.fixture
def counter(migrated_database):
    return lambda: QueryCounter(migrated_database.make("db"))


@pytest.fixture(autouse=True)
def seeded(migrated_database):
    schema = migrated_database.make("schema")
    tables = ["el_comments", "el_posts", "el_author_tag", "el_tags", "el_authors"]
    for table in tables:
        schema.drop_table(table)

    schema.create_table("el_authors", lambda t: (t.id(), t.string("name"), t.timestamps()))
    schema.create_table("el_posts", lambda t: (
        t.id(), t.string("title"), t.big_integer("author_id").nullable(), t.timestamps(),
    ))
    schema.create_table("el_comments", lambda t: (
        t.id(), t.string("body"), t.big_integer("post_id").nullable(), t.timestamps(),
    ))
    schema.create_table("el_tags", lambda t: (t.id(), t.string("label"), t.timestamps()))
    schema.create_table("el_author_tag", lambda t: (
        t.id(), t.big_integer("author_id"), t.big_integer("tag_id"),
    ))

    authors = [Author.create({"name": f"author-{i}"}) for i in range(3)]
    for author in authors:
        for j in range(2):
            post = Post.create(
                {"title": f"{author.get_attribute('name')}-post-{j}",
                 "author_id": author.get_attribute("id")}
            )
            Comment.create({"body": "c1", "post_id": post.get_attribute("id")})
            Comment.create({"body": "c2", "post_id": post.get_attribute("id")})

    tag = Tag.create({"label": "python"})
    other = Tag.create({"label": "orm"})
    for author in authors:
        author.tags().attach(tag.get_attribute("id"))
    authors[0].tags().attach(other.get_attribute("id"))

    yield {"authors": authors, "tags": [tag, other]}

    for table in tables:
        schema.drop_table(table)


class TestHasManyEagerLoading:
    def test_lazy_loading_is_n_plus_1(self, counter):
        """Baseline: without with_(), each parent costs a query."""
        with counter() as c:
            authors = Author.query().get()
            for author in authors:
                author.posts().get()
        assert c.count == 4  # 1 for authors + 3 for each author's posts

    def test_eager_loading_is_two_queries(self, counter):
        with counter() as c:
            authors = Author.with_("posts").get()
            for author in authors:
                author.posts().get()
        assert c.count == 2  # 1 for authors + 1 for all posts

    def test_eager_loaded_results_are_correct(self):
        authors = Author.with_("posts").order_by("id").get()
        for author in authors:
            posts = author.posts().get()
            assert len(posts) == 2
            for post in posts:
                assert post.get_attribute("author_id") == author.get_attribute("id")

    def test_count_uses_the_cache(self, counter):
        with counter() as c:
            authors = Author.with_("posts").get()
            totals = [author.posts().count() for author in authors]
        assert totals == [2, 2, 2]
        assert c.count == 2

    def test_relation_loaded_flag(self):
        eager = Author.with_("posts").first()
        lazy = Author.query().first()
        assert eager.relation_loaded("posts") is True
        assert lazy.relation_loaded("posts") is False

    def test_parent_without_children_gets_an_empty_collection(self, counter):
        Author.create({"name": "childless"})
        authors = Author.with_("posts").get()
        childless = [a for a in authors if a.get_attribute("name") == "childless"][0]
        assert len(childless.posts().get()) == 0

    def test_empty_result_set_issues_no_relation_query(self, counter):
        with counter() as c:
            Author.query().where("name", "nobody").with_("posts").get()
        assert c.count == 1


class TestBelongsToEagerLoading:
    def test_eager_loading_the_parent_is_two_queries(self, counter):
        with counter() as c:
            posts = Post.with_("author").get()
            for post in posts:
                post.author().first()
        assert c.count == 2

    def test_belongs_to_resolves_the_right_owner(self):
        posts = Post.with_("author").get()
        for post in posts:
            author = post.author().first()
            assert author.get_attribute("id") == post.get_attribute("author_id")

    def test_duplicate_foreign_keys_are_queried_once(self, counter):
        # Six posts share three authors — the IN clause must dedupe.
        with counter() as c:
            posts = Post.with_("author").get()
            [p.author().first() for p in posts]
        assert len(posts) == 6
        assert c.count == 2

    def test_null_foreign_key_yields_none(self):
        Post.create({"title": "orphan", "author_id": None})
        posts = Post.with_("author").get()
        orphan = [p for p in posts if p.get_attribute("title") == "orphan"][0]
        assert orphan.author().first() is None


class TestHasOneEagerLoading:
    def test_has_one_loads_a_single_model(self, counter):
        with counter() as c:
            authors = Author.with_("latest_post").get()
            singles = [a.latest_post().get() for a in authors]
        assert c.count == 2
        assert all(isinstance(s, Post) for s in singles)


class TestBelongsToManyEagerLoading:
    def test_pivot_relation_is_two_queries(self, counter):
        with counter() as c:
            authors = Author.with_("tags").get()
            for author in authors:
                author.tags().get()
        assert c.count == 2

    def test_pivot_rows_land_on_the_right_parent(self):
        authors = Author.with_("tags").order_by("id").get()
        counts = [len(a.tags().get()) for a in authors]
        assert counts == [2, 1, 1]

    def test_pivot_alias_is_not_leaked_as_a_real_column(self):
        author = Author.with_("tags").order_by("id").first()
        tag = author.tags().get()[0]
        assert tag.get_attribute("label") in ("python", "orm")


class TestMultipleAndInvalidRelations:
    def test_two_relations_cost_one_query_each(self, counter):
        with counter() as c:
            posts = Post.with_("author", "comments").get()
            for post in posts:
                post.author().first()
                post.comments().get()
        assert c.count == 3  # posts + authors + comments

    def test_repeated_relation_names_are_deduped(self, counter):
        with counter() as c:
            Post.with_("author", "author").get()
        assert c.count == 2

    def test_without_removes_a_queued_relation(self, counter):
        with counter() as c:
            Post.query().with_("author").without("author").get()
        assert c.count == 1

    def test_unknown_relation_raises(self):
        with pytest.raises(RelationNotFoundError):
            Author.with_("nonexistent").get()

    def test_lazy_access_still_works_after_eager_loading_another_relation(self, counter):
        with counter() as c:
            posts = Post.with_("author").get()
            posts[0].comments().get()
        assert c.count == 3  # posts + authors + one lazy comments query
