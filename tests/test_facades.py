"""Facades: static proxying, and not resolving the container too early."""

import pytest

from services.container.application import Application, Container
from services.facades.base import Facade


class Dummy:
    def __init__(self):
        self.calls = []

    def greet(self, name):
        self.calls.append(name)
        return f"hello {name}"

    value = 42


class DummyFacade(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "dummy.service"


class TestProxying:
    @pytest.fixture(autouse=True)
    def bound(self, migrated_database):
        service = Dummy()
        migrated_database.instance("dummy.service", service)
        DummyFacade._app = migrated_database
        yield service
        DummyFacade._app = None

    def test_forwards_method_calls(self, bound):
        assert DummyFacade.greet("world") == "hello world"
        assert bound.calls == ["world"]

    def test_forwards_attributes(self):
        assert DummyFacade.value == 42

    def test_unknown_public_attribute_raises_from_the_service(self):
        with pytest.raises(AttributeError):
            DummyFacade.no_such_method


class TestIntrospectionSafety:
    """A facade must not fabricate dunder/private attributes.

    pytest collection, `inspect`, `copy` and `pickle` all probe names like
    `__wrapped__` and `__test__` on module-level objects. Forwarding those to
    the container resolved it before the app booted: `getInstance()` built an
    empty fallback container and claimed the global, so the real application's
    bindings were never visible. Modules that imported a facade at module level
    without also importing `bootstrap.app` failed on their own and only passed
    when another test file happened to boot the app first.
    """

    @pytest.mark.parametrize(
        "name", ["__wrapped__", "__test__", "__iter__", "_private"]
    )
    def test_dunder_and_private_access_raises_attribute_error(self, name):
        # `__bases__`, `__name__` etc. are deliberately absent here — those are
        # real class attributes, so `__getattr__` is never consulted for them.
        with pytest.raises(AttributeError):
            getattr(DummyFacade, name)

    def test_probing_a_facade_does_not_claim_the_global_container(self):
        previous = Container._instance
        Container.setInstance(None)
        try:
            with pytest.raises(AttributeError):
                DummyFacade.__wrapped__
            assert Container._instance is None
        finally:
            Container.setInstance(previous)

    def test_a_fallback_container_never_shadows_the_real_app(self, tmp_path):
        previous = Container._instance
        Container.setInstance(None)
        try:
            # Something resolves the container before boot — getInstance()
            # hands back a bare fallback and stores it.
            fallback = Container.getInstance()
            assert not isinstance(fallback, Application)

            # The real application must displace it, not defer to it.
            app = Application(str(tmp_path))
            assert Container.getInstance() is app
        finally:
            Container.setInstance(previous)

    def test_a_scratch_app_still_defers_to_a_real_app(self, tmp_path):
        previous = Container._instance
        try:
            real = Application(str(tmp_path), bind_as_global=True)
            Application(str(tmp_path))  # scratch — must not steal the global
            assert Container.getInstance() is real
        finally:
            Container.setInstance(previous)
