"""BelongsToMany.attach/detach/sync respect a tenant column on the pivot table."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest

from craft.facades import Tenant
from craft.migrations.schema import SchemaBuilder
from craft.orm.model import Model
from craft.orm.tenant_scoped import TenantScoped

ACME = "11111111-1111-1111-1111-111111111111"
BETA = "22222222-2222-2222-2222-222222222222"


class Project(TenantScoped, Model):
    __table__ = "rel_projects"
    fillable = ["name"]
    uses_uuid = False

    def tags(self):
        return self.belongs_to_many(Tag, pivot_table="rel_project_tag")


class Tag(TenantScoped, Model):
    __table__ = "rel_tags"
    fillable = ["label"]
    uses_uuid = False

    def projects(self):
        return self.belongs_to_many(Project, pivot_table="rel_project_tag")


class Widget(Model):
    __table__ = "rel_widgets"
    fillable = ["name"]
    uses_uuid = False

    def labels(self):
        return self.belongs_to_many(Label, pivot_table="rel_widget_label")


class Label(Model):
    __table__ = "rel_labels"
    fillable = ["name"]
    uses_uuid = False


@pytest.fixture
def tenanted_pivot_tables(migrated_database):
    """A many-to-many pair whose pivot table carries tenant_id."""
    schema = SchemaBuilder(migrated_database.make("db"))
    for table in ("rel_project_tag", "rel_projects", "rel_tags"):
        schema.drop_if_exists(table)
    schema.create_table("rel_projects", lambda t: (
        t.id(type="integer"), t.string("name"), t.tenant_scoped(references=None), t.timestamps(),
    ))
    schema.create_table("rel_tags", lambda t: (
        t.id(type="integer"), t.string("label"), t.tenant_scoped(references=None), t.timestamps(),
    ))
    schema.create_table("rel_project_tag", lambda t: (
        t.id(type="integer"),
        t.integer("project_id"),
        t.integer("tag_id"),
        t.tenant_scoped(references=None),
    ))
    yield
    for table in ("rel_project_tag", "rel_projects", "rel_tags"):
        schema.drop_if_exists(table)


@pytest.fixture
def untenanted_pivot_tables(migrated_database):
    """A many-to-many pair whose pivot table has no tenant column at all."""
    schema = SchemaBuilder(migrated_database.make("db"))
    for table in ("rel_widget_label", "rel_widgets", "rel_labels"):
        schema.drop_if_exists(table)
    schema.create_table("rel_widgets", lambda t: (t.id(type="integer"), t.string("name"), t.timestamps()))
    schema.create_table("rel_labels", lambda t: (t.id(type="integer"), t.string("name"), t.timestamps()))
    schema.create_table("rel_widget_label", lambda t: (
        t.id(type="integer"), t.integer("widget_id"), t.integer("label_id"),
    ))
    yield
    for table in ("rel_widget_label", "rel_widgets", "rel_labels"):
        schema.drop_if_exists(table)


def test_attach_stamps_the_bound_tenant_on_the_pivot_row(tenanted_pivot_tables):
    with Tenant.scope(ACME):
        project = Project.create({"name": "P1"})
        tag = Tag.create({"label": "T1"})
        project.tags().attach(tag.id)

        from craft.facades import DB

        row = DB.table("rel_project_tag").where("project_id", project.id).first()
        assert row["tenant_id"] == ACME


def test_detach_never_reaches_another_tenants_pivot_row(tenanted_pivot_tables):
    with Tenant.scope(ACME):
        acme_project = Project.create({"name": "P-acme"})
        acme_tag = Tag.create({"label": "T-acme"})
        acme_project.tags().attach(acme_tag.id)

    with Tenant.scope(BETA):
        beta_project = Project.create({"name": "P-beta"})
        beta_tag = Tag.create({"label": "T-beta"})
        beta_project.tags().attach(beta_tag.id)

    from craft.facades import DB

    # BETA's detach() must not touch ACME's pivot row, even by coincidence of
    # matching foreign keys (both projects/tags start at id=1 in fresh tables).
    with Tenant.scope(BETA):
        beta_project.tags().detach(beta_tag.id)

    with Tenant.scope(ACME):
        surviving = DB.table("rel_project_tag").where("project_id", acme_project.id).first()
        assert surviving is not None


def test_sync_replaces_only_the_bound_tenants_pivot_rows(tenanted_pivot_tables):
    with Tenant.scope(ACME):
        project = Project.create({"name": "P2"})
        tag_a = Tag.create({"label": "A"})
        tag_b = Tag.create({"label": "B"})
        project.tags().attach(tag_a.id)

        project.tags().sync([tag_b.id])

        from craft.facades import DB

        rows = DB.table("rel_project_tag").where("project_id", project.id).get()
        assert [row["tag_id"] for row in rows] == [tag_b.id]
        assert all(row["tenant_id"] == ACME for row in rows)


def test_attach_and_detach_are_unchanged_when_the_pivot_has_no_tenant_column(
    untenanted_pivot_tables,
):
    """No tenant handling kicks in for a plain (non-tenant-scoped) pivot."""
    widget = Widget.create({"name": "W1"})
    label = Label.create({"name": "L1"})

    widget.labels().attach(label.id)

    from craft.facades import DB

    row = DB.table("rel_widget_label").where("widget_id", widget.id).first()
    assert row is not None
    assert "tenant_id" not in row

    widget.labels().detach(label.id)
    assert DB.table("rel_widget_label").where("widget_id", widget.id).first() is None
