"""Event dispatcher and API resources."""
# Codepy Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import json

import pytest

from services.events.dispatcher import EventDispatcher
from services.events.event import Event
from services.resources.resource import Resource, ResourceCollection


class Fired(Event):
    def __init__(self, payload=None):
        self.payload = payload


class Derived(Fired):
    pass


class RecordingListener:
    seen = []

    def handle(self, event):
        RecordingListener.seen.append(event)
        return "handled"


@pytest.fixture(autouse=True)
def clear_listener_state():
    RecordingListener.seen = []
    yield
    RecordingListener.seen = []


@pytest.fixture
def dispatcher():
    return EventDispatcher()


class TestRegistration:
    def test_a_single_listener_needs_no_list(self, dispatcher):
        # Requiring a list made the obvious call raise
        # "'type' object is not iterable".
        dispatcher.listen(Fired, RecordingListener)
        dispatcher.dispatch(Fired())
        assert len(RecordingListener.seen) == 1

    def test_a_list_of_listeners_also_works(self, dispatcher):
        hits = []
        dispatcher.listen(Fired, [lambda e: hits.append(1), lambda e: hits.append(2)])
        dispatcher.dispatch(Fired())
        assert hits == [1, 2]

    def test_listeners_accumulate_across_calls(self, dispatcher):
        hits = []
        dispatcher.listen(Fired, lambda e: hits.append("a"))
        dispatcher.listen(Fired, lambda e: hits.append("b"))
        dispatcher.dispatch(Fired())
        assert hits == ["a", "b"]

    def test_has_listeners(self, dispatcher):
        assert dispatcher.has_listeners(Fired) is False
        dispatcher.listen(Fired, RecordingListener)
        assert dispatcher.has_listeners(Fired) is True

    def test_forget_removes_them(self, dispatcher):
        dispatcher.listen(Fired, RecordingListener)
        dispatcher.forget(Fired)
        assert dispatcher.has_listeners(Fired) is False

    def test_subscriber_registers_its_own_listeners(self, dispatcher):
        hits = []

        class Subscriber:
            def subscribe(self, events):
                events.listen(Fired, lambda e: hits.append("from-subscriber"))

        dispatcher.subscribe(Subscriber)
        dispatcher.dispatch(Fired())
        assert hits == ["from-subscriber"]


class TestDispatching:
    def test_a_plain_function_listener_is_called(self, dispatcher):
        hits = []
        dispatcher.listen(Fired, lambda e: hits.append(e))
        dispatcher.dispatch(Fired("x"))
        assert len(hits) == 1

    def test_the_event_instance_reaches_the_listener(self, dispatcher):
        dispatcher.listen(Fired, RecordingListener)
        event = Fired("payload")
        dispatcher.dispatch(event)
        assert RecordingListener.seen[0] is event

    def test_dispatch_returns_listener_responses(self, dispatcher):
        dispatcher.listen(Fired, [lambda e: "a", lambda e: "b"])
        assert dispatcher.dispatch(Fired()) == ["a", "b"]

    def test_dispatching_with_no_listeners_is_harmless(self, dispatcher):
        assert dispatcher.dispatch(Fired()) == []

    def test_a_base_class_listener_hears_subclasses(self, dispatcher):
        # Matching on exact class meant a listener on a base event never fired
        # for the specific events that actually get dispatched.
        hits = []
        dispatcher.listen(Fired, lambda e: hits.append(type(e).__name__))
        dispatcher.dispatch(Derived())
        assert hits == ["Derived"]

    def test_a_subclass_listener_does_not_hear_the_base(self, dispatcher):
        hits = []
        dispatcher.listen(Derived, lambda e: hits.append(1))
        dispatcher.dispatch(Fired())
        assert hits == []

    def test_wildcard_listeners_hear_everything(self, dispatcher):
        hits = []
        dispatcher.listen("*", lambda e: hits.append(type(e).__name__))
        dispatcher.dispatch(Fired())
        dispatcher.dispatch(Derived())
        assert hits == ["Fired", "Derived"]

    def test_until_stops_at_the_first_response(self, dispatcher):
        calls = []

        def first(event):
            calls.append("first")
            return None

        def second(event):
            calls.append("second")
            return "answer"

        def third(event):
            calls.append("third")
            return "never reached"

        dispatcher.listen(Fired, [first, second, third])
        assert dispatcher.until(Fired()) == "answer"
        assert calls == ["first", "second"]

    def test_fire_is_an_alias_of_dispatch(self, dispatcher):
        dispatcher.listen(Fired, lambda e: "ok")
        assert dispatcher.fire(Fired()) == ["ok"]


class TestListenerResolution:
    def test_listener_classes_are_instantiated(self, dispatcher):
        dispatcher.listen(Fired, RecordingListener)
        dispatcher.dispatch(Fired())
        assert len(RecordingListener.seen) == 1

    def test_a_listener_instance_is_used_as_is(self, dispatcher):
        instance = RecordingListener()
        dispatcher.listen(Fired, instance)
        dispatcher.dispatch(Fired())
        assert len(RecordingListener.seen) == 1

    def test_listeners_resolve_through_the_container(self, migrated_database):
        class NeedsDatabase:
            def __init__(self, db=None):
                self.db = db

            def handle(self, event):
                return "resolved"

        dispatcher = EventDispatcher(migrated_database)
        dispatcher.listen(Fired, NeedsDatabase)
        assert dispatcher.dispatch(Fired()) == ["resolved"]


# -- resources -------------------------------------------------------------------


class Model:
    """Stands in for a real model whose to_dict() exposes everything."""

    def to_dict(self):
        return {"id": 1, "title": "Post", "secret": "must not leak"}

    def get_attribute(self, key):
        return self.to_dict().get(key)


class GeneratedStyleResource(Resource):
    """What `craft make:resource` emits."""

    def to_array(self, request=None):
        return {"id": self.resource.get_attribute("id")}


class ToDictResource(Resource):
    """A subclass that overrode to_dict() instead."""

    def to_dict(self):
        return {"id": self.resource.get_attribute("id")}


class TestResourceTransformation:
    def test_to_array_override_is_used(self):
        assert GeneratedStyleResource(Model()).to_array() == {"id": 1}

    def test_to_dict_override_is_also_used(self):
        # The base class read `self.resource.to_dict()`, so a subclass that
        # defined to_dict() was ignored and the whole model was emitted — the
        # exact opposite of what an API Resource is for.
        assert ToDictResource(Model()).to_dict() == {"id": 1}

    def test_a_to_dict_override_does_not_leak_the_model(self):
        assert "secret" not in ToDictResource(Model()).to_array()

    def test_a_to_array_override_does_not_leak_the_model(self):
        assert "secret" not in GeneratedStyleResource(Model()).to_dict()

    def test_the_two_hooks_agree(self):
        resource = GeneratedStyleResource(Model())
        assert resource.to_array() == resource.to_dict()

    def test_without_an_override_the_model_is_passed_through(self):
        assert Resource(Model()).to_array() == Model().to_dict()

    def test_a_plain_dict_is_passed_through(self):
        assert Resource({"a": 1}).to_array() == {"a": 1}

    def test_an_unknown_object_yields_an_empty_dict(self):
        assert Resource(object()).to_array() == {}


class TestResourceResponse:
    def test_response_serialises_the_transformation(self):
        response = GeneratedStyleResource(Model()).response()
        body = json.loads(response.to_starlette().body)
        assert body == {"id": 1}

    def test_response_status_is_honoured(self):
        assert GeneratedStyleResource(Model()).response(201).to_starlette().status_code == 201

    def test_when_includes_conditionally(self):
        resource = GeneratedStyleResource(Model())
        assert resource.when(True, "shown") == "shown"
        assert resource.when(False, "shown") is None
        assert resource.when(False, "shown", "fallback") == "fallback"


class TestResourceCollection:
    def test_collection_transforms_every_item(self):
        collection = GeneratedStyleResource.collection([Model(), Model()])
        assert collection.to_array() == [{"id": 1}, {"id": 1}]

    def test_collection_is_a_resource_collection(self):
        assert isinstance(GeneratedStyleResource.collection([]), ResourceCollection)

    def test_collection_length(self):
        assert len(GeneratedStyleResource.collection([Model(), Model()])) == 2

    def test_collection_response_wraps_in_data(self):
        response = GeneratedStyleResource.collection([Model()]).response()
        assert json.loads(response.to_starlette().body) == {"data": [{"id": 1}]}

    def test_pagination_metadata_survives(self):
        from services.support.collection import Collection

        items = Collection([Model()])
        items.pagination = {"total": 1, "per_page": 15, "current_page": 1, "last_page": 1}

        body = json.loads(GeneratedStyleResource.collection(items).response().to_starlette().body)
        assert body["meta"]["total"] == 1

    def test_extra_meta_can_be_added(self):
        response = GeneratedStyleResource.collection([Model()]).response(meta={"version": "1"})
        assert json.loads(response.to_starlette().body)["meta"] == {"version": "1"}

    def test_an_empty_collection_is_fine(self):
        assert GeneratedStyleResource.collection([]).to_array() == []
