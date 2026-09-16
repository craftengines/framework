"""Model.save writes only changed columns and never crosses the loaded tenant."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from typing import Any

import pytest

from craft.container.application import Container
from craft.orm.model import Model
from craft.orm.tenancy import TenantManager
from craft.orm.tenant_scoped import TenantScoped


class Ticket(Model):
    __table__ = "tracking_tickets"
    fillable = ["title", "status"]
    casts = {"meta": "json"}


class Invoice(TenantScoped, Model):
    __table__ = "tracking_invoices"
    fillable = ["number", "tenant_id"]


@pytest.fixture(autouse=True)
def tables(migrated_database):
    schema = migrated_database.make("schema")
    for table in ("tracking_tickets", "tracking_invoices"):
        schema.drop_table(table)
    schema.create_table("tracking_tickets", lambda t: (
        t.id(), t.string("title").nullable(), t.string("status").nullable(),
        t.text("meta").nullable(), t.timestamps(),
    ))
    schema.create_table("tracking_invoices", lambda t: (
        t.id(), t.string("number").nullable(), t.string("tenant_id").nullable(), t.timestamps(),
    ))
    yield
    for table in ("tracking_tickets", "tracking_invoices"):
        schema.drop_table(table)


def _capture_statements(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    manager = Container.getInstance().make("db")
    captured: list[str] = []
    original = manager.statement

    def spy(query: str, *args: Any, **kwargs: Any) -> Any:
        captured.append(query)
        return original(query, *args, **kwargs)

    monkeypatch.setattr(manager, "statement", spy)
    return captured


def test_concurrent_edits_to_different_columns_both_survive() -> None:
    created = Ticket.create({"title": "Draft", "status": "open"})
    first = Ticket.find(created.id)
    second = Ticket.find(created.id)
    first.set_attribute("title", "Final")
    second.set_attribute("status", "closed")
    first.save()
    second.save()
    reloaded = Ticket.find(created.id)
    assert (reloaded.title, reloaded.status) == ("Final", "closed")


def test_a_clean_model_issues_no_update(monkeypatch: pytest.MonkeyPatch) -> None:
    ticket = Ticket.find(Ticket.create({"title": "Draft"}).id)
    statements = _capture_statements(monkeypatch)
    ticket.save()
    assert not [query for query in statements if query.lstrip().upper().startswith("UPDATE")]


def test_dirty_state_resets_after_save() -> None:
    ticket = Ticket.find(Ticket.create({"title": "Draft"}).id)
    ticket.set_attribute("title", "Final")
    assert ticket.get_dirty() == {"title": "Final"}
    ticket.save()
    assert not ticket.is_dirty()


def test_in_place_mutation_of_a_cast_value_is_detected() -> None:
    ticket = Ticket.create({"title": "Draft"})
    ticket.set_attribute("meta", {"tags": []})
    ticket.save()
    ticket = Ticket.find(ticket.id)
    ticket.meta["tags"].append("urgent")
    assert "meta" in ticket.get_dirty()
    ticket.save()
    assert Ticket.find(ticket.id).meta == {"tags": ["urgent"]}


def test_update_never_reaches_a_row_of_another_tenant() -> None:
    with TenantManager().scope("tenant-b"):
        victim = Invoice.create({"number": "B-1"})
    with TenantManager().scope("tenant-a"):
        forged = Invoice({"id": victim.id, "number": "A-1", "tenant_id": "tenant-a"})
        forged.set_attribute("number", "HIJACKED")
        forged.save()
    with TenantManager().scope("tenant-b"):
        assert Invoice.find(victim.id).number == "B-1"


def test_delete_never_reaches_a_row_of_another_tenant() -> None:
    with TenantManager().scope("tenant-b"):
        victim = Invoice.create({"number": "B-2"})
    with TenantManager().scope("tenant-a"):
        Invoice({"id": victim.id, "tenant_id": "tenant-a"}).delete()
    with TenantManager().scope("tenant-b"):
        assert Invoice.find(victim.id) is not None
