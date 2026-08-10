"""Service container: binding, resolution, autowiring and global scoping."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest

from craft.container.application import Application, Container


class Engine:
    pass


class Wheels:
    pass


class Car:
    def __init__(self, engine: Engine, wheels: Wheels):
        self.engine = engine
        self.wheels = wheels


class Countable:
    instances = 0

    def __init__(self):
        Countable.instances += 1


@pytest.fixture
def container():
    return Container()


class TestBinding:
    def test_bind_resolves_a_new_instance_each_time(self, container):
        container.bind("engine", lambda c: Engine())
        assert container.make("engine") is not container.make("engine")

    def test_singleton_resolves_the_same_instance(self, container):
        container.singleton("engine", lambda c: Engine())
        assert container.make("engine") is container.make("engine")

    def test_instance_registers_an_existing_object(self, container):
        engine = Engine()
        container.instance("engine", engine)
        assert container.make("engine") is engine

    def test_alias_resolves_to_the_target(self, container):
        engine = Engine()
        container.instance("engine", engine)
        container.alias("engine", "motor")
        assert container.make("motor") is engine

    def test_singleton_factory_runs_once(self, container):
        Countable.instances = 0
        container.singleton("counted", lambda c: Countable())
        container.make("counted")
        container.make("counted")
        assert Countable.instances == 1

    def test_unbound_string_raises(self, container):
        with pytest.raises(KeyError):
            container.make("nothing.bound.here")


class TestAutowiring:
    def test_resolves_constructor_dependencies_from_annotations(self, container):
        car = container.make(Car)
        assert isinstance(car.engine, Engine)
        assert isinstance(car.wheels, Wheels)

    def test_explicit_parameters_win(self, container):
        engine = Engine()
        car = container.make(Car, {"engine": engine})
        assert car.engine is engine

    def test_bound_dependencies_are_reused(self, container):
        engine = Engine()
        container.instance(Engine, engine)
        assert container.make(Car).engine is engine


class TestGlobalInstance:
    """Constructing a container must never hijack the global singleton."""

    def setup_method(self):
        self._previous = Container._instance

    def teardown_method(self):
        Container.setInstance(self._previous)

    def test_constructing_a_container_does_not_claim_the_global(self):
        current = Container.getInstance()
        Container()
        assert Container.getInstance() is current

    def test_constructing_a_scratch_application_does_not_claim_the_global(self, tmp_path):
        current = Container.getInstance()
        Application(str(tmp_path))
        assert Container.getInstance() is current

    def test_make_current_claims_explicitly(self, tmp_path):
        scratch = Application(str(tmp_path))
        scratch.make_current()
        assert Container.getInstance() is scratch

    def test_bind_as_global_true_claims(self, tmp_path):
        scratch = Application(str(tmp_path), bind_as_global=True)
        assert Container.getInstance() is scratch

    def test_bind_as_global_false_never_claims(self, tmp_path):
        Container.setInstance(None)
        scratch = Application(str(tmp_path), bind_as_global=False)
        assert Container.getInstance() is not scratch

    def test_the_first_application_claims_an_unclaimed_global(self, tmp_path):
        Container.setInstance(None)
        first = Application(str(tmp_path))
        assert Container.getInstance() is first

    def test_scoped_swaps_then_restores(self, tmp_path):
        original = Container.getInstance()
        scratch = Application(str(tmp_path), bind_as_global=False)

        with Container.scoped_instance(scratch):
            assert Container.getInstance() is scratch

        assert Container.getInstance() is original

    def test_scoped_restores_even_when_the_body_raises(self, tmp_path):
        original = Container.getInstance()
        scratch = Application(str(tmp_path), bind_as_global=False)

        with pytest.raises(RuntimeError):
            with Container.scoped_instance(scratch):
                raise RuntimeError("boom")

        assert Container.getInstance() is original


class TestApplication:
    def test_registers_itself_under_app(self, tmp_path):
        app = Application(str(tmp_path), bind_as_global=False)
        assert app.make("app") is app

    def test_base_path_is_stored(self, tmp_path):
        assert Application(str(tmp_path), bind_as_global=False).base_path == str(tmp_path)

    def test_providers_boot_once(self, tmp_path):
        booted = []

        class Provider:
            def __init__(self, app):
                self.app = app

            def register(self):
                pass

            def boot(self):
                booted.append(1)

        app = Application(str(tmp_path), bind_as_global=False)
        app.register_provider(Provider)
        app.boot()
        app.boot()
        assert len(booted) == 1

    def test_a_provider_registered_after_boot_boots_immediately(self, tmp_path):
        booted = []

        class Provider:
            def __init__(self, app):
                self.app = app

            def register(self):
                pass

            def boot(self):
                booted.append(1)

        app = Application(str(tmp_path), bind_as_global=False)
        app.boot()
        app.register_provider(Provider)
        assert len(booted) == 1
