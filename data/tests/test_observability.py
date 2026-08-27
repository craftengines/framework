"""Correlation, metrics and error reporting.

The question behind all of it: when four instances are serving and one of them
misbehaves, can the log line, the latency number and the exception report be
tied back to the single request that caused them.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import json
import logging
import threading

import pytest
from starlette.testclient import TestClient

from bootstrap.app import app, asgi_app
from craft.exceptions.handler import ExceptionHandler
from craft.support import context
from craft.support.logging import JsonFormatter, RequestContextFilter, TextFormatter
from craft.support.metrics import MetricsRegistry


@pytest.fixture(scope="module", autouse=True)
def routes(migrated_database):
    """A route inside the middleware stack.

    The probes are mounted outside it on purpose, so they carry no request id
    and are not counted - a scrape every ten seconds would otherwise dominate
    the request metrics it exists to report.
    """
    from craft.facades import Route

    def ping(request):
        return {"request_id": context.request_id()}

    def boom(request):
        raise RuntimeError("SERVER_FAULT")

    Route.get("/t/obs-ping", ping).name("t.obs.ping")
    Route.get("/t/obs-boom", boom).name("t.obs.boom")
    yield


@pytest.fixture
def client(migrated_database):
    return TestClient(asgi_app)


@pytest.fixture
def registry():
    return MetricsRegistry()


class TestRequestContext:
    def test_it_is_empty_outside_a_request(self):
        assert context.request_id() is None
        assert context.current() == {}

    def test_bind_restores_the_previous_context(self):
        with context.bind(request_id="outer"):
            with context.bind(request_id="inner"):
                assert context.request_id() == "inner"
            assert context.request_id() == "outer"
        assert context.request_id() is None

    def test_each_thread_sees_its_own_context(self):
        """A pooled thread reused by the next request must not inherit the
        previous request's identity - the reason this is a ContextVar."""
        seen = {}
        started = threading.Barrier(2)

        def work(name):
            with context.bind(request_id=name):
                started.wait(timeout=5)
                seen[name] = context.request_id()

        threads = [threading.Thread(target=work, args=(n,)) for n in ("a", "b")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        assert seen == {"a": "a", "b": "b"}

    @pytest.mark.parametrize(
        "candidate",
        ["", None, "x" * 200, "has space", "has\nnewline", 'quote"inside'],
    )
    def test_an_untrustworthy_inbound_identifier_is_rejected(self, candidate):
        assert context.sanitize_request_id(candidate) is None

    def test_a_well_formed_inbound_identifier_is_kept(self):
        assert context.sanitize_request_id("abc-123_XY.7:8") == "abc-123_XY.7:8"


class TestCorrelationOverHttp:
    def test_every_response_carries_a_request_id(self, client):
        response = client.get("/t/obs-ping")
        assert response.headers["X-Request-ID"]

    def test_the_controller_sees_the_same_identifier_as_the_header(self, client):
        """The context has to survive the hop onto the worker thread, or the
        identifier in the log line is not the one the client was given."""
        response = client.get("/t/obs-ping")
        assert response.json()["request_id"] == response.headers["X-Request-ID"]

    def test_two_requests_get_different_identifiers(self, client):
        first = client.get("/t/obs-ping").headers["X-Request-ID"]
        second = client.get("/t/obs-ping").headers["X-Request-ID"]
        assert first != second

    def test_an_inbound_identifier_is_echoed(self, client):
        response = client.get("/t/obs-ping", headers={"X-Request-ID": "trace-abc-1"})
        assert response.headers["X-Request-ID"] == "trace-abc-1"

    def test_a_forged_identifier_is_replaced_not_echoed(self, client):
        """A newline in the header would forge log entries downstream."""
        forged = "abc\nWARNING fake log line"
        response = client.get("/t/obs-ping", headers={"X-Request-ID": forged})
        assert response.headers["X-Request-ID"] != forged
        assert "\n" not in response.headers["X-Request-ID"]

    def test_the_context_does_not_leak_to_the_next_request(self, client):
        client.get("/t/obs-ping", headers={"X-Request-ID": "leaky-1"})
        assert context.request_id() is None


class TestStructuredLogging:
    def _record(self, **extra):
        record = logging.LogRecord(
            "craft", logging.INFO, __file__, 10, "something happened", None, None
        )
        for key, value in extra.items():
            setattr(record, key, value)
        return record

    def test_json_lines_carry_the_request_id_as_a_field(self):
        payload = json.loads(JsonFormatter().format(self._record(request_id="r-1")))
        assert payload["request_id"] == "r-1"
        assert payload["level"] == "INFO"
        assert payload["message"] == "something happened"

    def test_extra_fields_survive_into_the_payload(self):
        payload = json.loads(JsonFormatter().format(self._record(order_id=42)))
        assert payload["order_id"] == 42

    def test_a_value_that_cannot_serialise_does_not_lose_the_line(self):
        payload = json.loads(JsonFormatter().format(self._record(thing=object())))
        assert "thing" in payload

    def test_an_exception_is_rendered_as_a_structured_field(self):
        try:
            raise ValueError("BOOM")
        except ValueError:
            import sys

            record = self._record()
            record.exc_info = sys.exc_info()

        payload = json.loads(JsonFormatter().format(record))
        assert payload["exception"]["type"] == "ValueError"
        assert "ValueError" in payload["exception"]["stack"]

    def test_the_text_format_appends_the_request_id(self):
        formatter = TextFormatter(TextFormatter.DEFAULT_FORMAT)
        assert "[request_id=r-9]" in formatter.format(self._record(request_id="r-9"))

    def test_the_filter_copies_the_context_onto_the_record(self):
        record = self._record()
        with context.bind(request_id="r-2", method="POST"):
            RequestContextFilter().filter(record)
        assert record.request_id == "r-2"
        assert record.method == "POST"


class TestMetrics:
    def test_a_counter_accumulates_per_label_combination(self, registry):
        registry.increment("craft_requests_total", route="/a", status="200")
        registry.increment("craft_requests_total", route="/a", status="200")
        registry.increment("craft_requests_total", route="/b", status="500")

        counter = registry.get("craft_requests_total")
        assert counter.value(route="/a", status="200") == 2
        assert counter.value(route="/b", status="500") == 1

    def test_a_histogram_fills_cumulative_buckets(self, registry):
        for value in (0.001, 0.03, 2.0):
            registry.observe("craft_request_duration_seconds", value, route="/a")

        rendered = registry.render()
        assert 'craft_request_duration_seconds_bucket{route="/a",le="0.005"} 1' in rendered
        assert 'craft_request_duration_seconds_bucket{route="/a",le="0.05"} 2' in rendered
        assert 'craft_request_duration_seconds_bucket{route="/a",le="+Inf"} 3' in rendered
        assert 'craft_request_duration_seconds_count{route="/a"} 3' in rendered

    def test_the_exposition_declares_type_and_help(self, registry):
        registry.counter("craft_things_total", "Things that happened.")
        registry.increment("craft_things_total")

        rendered = registry.render()
        assert "# HELP craft_things_total Things that happened." in rendered
        assert "# TYPE craft_things_total counter" in rendered

    def test_a_gauge_reads_at_scrape_time(self, registry):
        readings = {"value": 1}
        registry.gauge("craft_thing", "A thing.", lambda: readings["value"])
        assert "craft_thing 1" in registry.render()

        readings["value"] = 7
        assert "craft_thing 7" in registry.render()

    def test_a_gauge_that_raises_does_not_fail_the_scrape(self, registry):
        registry.counter("craft_kept_total", "Still reported.")
        registry.increment("craft_kept_total")

        def broken():
            raise RuntimeError("DEPENDENCY_UNAVAILABLE")

        registry.gauge("craft_broken", "Cannot be read.", broken)

        rendered = registry.render()
        assert "craft_kept_total 1" in rendered
        assert "craft_broken" not in rendered

    def test_label_values_are_escaped(self, registry):
        registry.increment("craft_things_total", label='a"b')
        assert chr(92) + '"' in registry.render()

    def test_disabling_the_registry_stops_recording(self, registry):
        registry.enabled = False
        registry.increment("craft_things_total")
        assert registry.render().strip() == ""

    def test_concurrent_recording_loses_nothing(self, registry):
        def work():
            for _ in range(200):
                registry.increment("craft_things_total", route="/a")

        threads = [threading.Thread(target=work) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)

        assert registry.get("craft_things_total").value(route="/a") == 800


class TestMetricsEndpoint:
    def test_it_is_absent_unless_enabled(self, client):
        """Off by default: the payload names every route and how often each is
        hit, which is reconnaissance when reachable from outside."""
        assert client.get("/metrics").status_code == 404

    def test_requests_are_counted_by_route(self, client):
        from craft.support.metrics import registry

        before = registry.get("craft_requests_total")
        labels = {"method": "GET", "route": "/t/obs-ping", "status": "200"}
        before_value = before.value(**labels) if before else 0

        client.get("/t/obs-ping")

        assert registry.get("craft_requests_total").value(**labels) == before_value + 1

    def test_duration_is_observed_for_every_request(self, client):
        from craft.support.metrics import registry

        before = registry.get("craft_request_duration_seconds")
        labels = {"method": "GET", "route": "/t/obs-ping"}
        before_count = before.count(**labels) if before else 0

        client.get("/t/obs-ping")

        assert registry.get("craft_request_duration_seconds").count(**labels) == before_count + 1

    def test_a_failing_request_is_counted_and_still_timed(self, client):
        from craft.support.metrics import registry

        exceptions = registry.get("craft_exceptions_total")
        before = exceptions.value(exception="RuntimeError") if exceptions else 0

        client.get("/t/obs-boom")

        counted = registry.get("craft_exceptions_total").value(exception="RuntimeError")
        assert counted == before + 1
        duration = registry.get("craft_request_duration_seconds")
        assert duration.count(method="GET", route="/t/obs-boom") >= 1


class TestErrorReporting:
    def test_a_reporter_receives_the_exception_and_the_request_context(self):
        handler = ExceptionHandler(app)
        received = []
        handler.reporter(lambda exc, ctx: received.append((exc, ctx)))

        with context.bind(request_id="r-77"):
            handler.report(RuntimeError("SERVER_FAULT"))

        assert len(received) == 1
        exception, request_context = received[0]
        assert isinstance(exception, RuntimeError)
        assert request_context["request_id"] == "r-77"

    def test_client_errors_are_not_reported_to_sinks(self):
        from craft.exceptions.handler import NotFoundHttpException

        handler = ExceptionHandler(app)
        received = []
        handler.reporter(lambda exc, ctx: received.append(exc))

        handler.report(NotFoundHttpException())

        assert received == []

    def test_a_failing_reporter_does_not_mask_the_exception(self):
        handler = ExceptionHandler(app)
        reached = []

        def broken(exc, ctx):
            raise RuntimeError("REPORTER_DOWN")

        handler.reporter(broken)
        handler.reporter(lambda exc, ctx: reached.append(exc))

        handler.report(RuntimeError("SERVER_FAULT"))

        assert len(reached) == 1
