"""Liveness and readiness probes for Craft Framework.

Two questions a load balancer and an orchestrator ask, and they are not the
same one. Liveness asks "is this process wedged, should it be killed" and must
touch nothing external: a probe that fails because the database is down gets
every healthy web instance restarted during a database incident, turning one
outage into two. Readiness asks "can this instance serve traffic right now"
and does check dependencies, so an instance whose pool is exhausted is taken
out of rotation instead of returning errors.

Category: Core Framework (HTTP).
Relations:
  - Routes are mounted by `engine/http/kernel.py` outside the middleware
    stack, so a probe costs no session load, no CSRF check and no user lookup.
  - Reads pool statistics from `engine/orm/connection.py`.
References:
  - Guide: `documentation/deployment.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional, Tuple

#: Wall-clock start of this process, for the uptime the liveness probe reports.
_STARTED_AT = time.time()


class HealthCheck:
    """One named dependency probe returning `(healthy, details)`."""

    __slots__ = ("name", "probe", "critical")

    def __init__(self, name: str, probe: Callable[[], Dict[str, Any]], *, critical: bool = True):
        self.name = name
        self.probe = probe
        #: A non-critical failure is reported but does not fail readiness, for
        #: dependencies the application degrades around rather than needs.
        self.critical = critical

    def run(self) -> Tuple[bool, Dict[str, Any]]:
        started = time.monotonic()
        try:
            details = self.probe() or {}
            healthy = bool(details.pop("healthy", True))
        except Exception as exc:
            return False, {
                "status": "fail",
                "error": type(exc).__name__,
                "duration_ms": round((time.monotonic() - started) * 1000, 2),
            }
        details["status"] = "pass" if healthy else "fail"
        details["duration_ms"] = round((time.monotonic() - started) * 1000, 2)
        return healthy, details


class HealthReporter:
    """Builds the liveness and readiness payloads.

    The checks are resolved lazily from the container, so a probe never boots a
    service that the request path has not booted yet.
    """

    def __init__(self, app: Any, checks: Optional[List[HealthCheck]] = None):
        self.app = app
        self._checks = checks if checks is not None else self.default_checks()

    # -- checks ----------------------------------------------------------------

    def default_checks(self) -> List[HealthCheck]:
        return [
            HealthCheck("database", self._check_database),
            HealthCheck("cache", self._check_cache, critical=False),
        ]

    def add_check(self, check: HealthCheck) -> "HealthReporter":
        self._checks.append(check)
        return self

    def _check_database(self) -> Dict[str, Any]:
        """A real round-trip plus the pool census.

        `SELECT 1` rather than an ORM call on purpose: it proves the socket and
        the server, not the schema. The pool numbers ride along because an
        instance whose pool is fully checked out is the one a load balancer
        should stop sending work to, and that is invisible from the outside.
        """
        db = self.app.make("db")
        db.statement("SELECT 1")
        connection = db.write_connection
        stats = connection.pool_stats
        return {
            "driver": connection.driver,
            "pool_open": stats["open"],
            "pool_idle": stats["idle"],
            "pool_size": connection.pool_size,
        }

    def _check_cache(self) -> Dict[str, Any]:
        cache = self.app.make("cache")
        key = "health.probe"
        cache.put(key, "1", 10)
        return {"healthy": cache.get(key) == "1", "store": type(cache.store).__name__}

    # -- payloads --------------------------------------------------------------

    def liveness(self) -> Tuple[Dict[str, Any], int]:
        """Is the process itself alive. Touches nothing external, never fails."""
        return {
            "status": "ok",
            "uptime_seconds": round(time.time() - _STARTED_AT, 1),
        }, 200

    def readiness(self) -> Tuple[Dict[str, Any], int]:
        """Can this instance serve traffic. 503 when a critical check fails."""
        results: Dict[str, Any] = {}
        ready = True
        for check in self._checks:
            healthy, details = check.run()
            results[check.name] = details
            if not healthy and check.critical:
                ready = False
        payload = {"status": "ok" if ready else "unavailable", "checks": results}
        return payload, 200 if ready else 503


def register_health_routes(app: Any, routes: List[Any], claimed: set) -> None:
    """Mount the probe routes, unless the application defined its own.

    Appended to the Starlette route list directly rather than through the
    router, which is what keeps them outside the middleware stack. An
    application route on the same path always wins: `claimed` carries the URIs
    the router already answers.
    """
    from starlette.responses import JSONResponse
    from starlette.routing import Route as StarletteRoute

    try:
        config = app.make("config")
        enabled = bool(config.get("framework.HEALTH_ROUTES_ENABLED", True))
        live_path = str(config.get("framework.HEALTH_LIVENESS_PATH", "/health"))
        ready_path = str(config.get("framework.HEALTH_READINESS_PATH", "/ready"))
    except Exception:
        enabled, live_path, ready_path = True, "/health", "/ready"

    if not enabled:
        return

    reporter = HealthReporter(app)

    def endpoint_for(producer: Callable[[], Tuple[Dict[str, Any], int]]) -> Callable:
        async def endpoint(request: Any) -> Any:
            payload, status = await _run_probe(producer)
            return JSONResponse(payload, status_code=status)

        return endpoint

    for path, producer in ((live_path, reporter.liveness), (ready_path, reporter.readiness)):
        if path in claimed:
            continue
        routes.append(
            StarletteRoute(path, endpoint=endpoint_for(producer), methods=["GET"])
        )

    register_metrics_route(app, routes, claimed)


def register_metrics_route(app: Any, routes: List[Any], claimed: set) -> None:
    """Mount the scrape endpoint, off by default.

    Off unless asked for, because the payload names every route the
    application serves and how often each is hit, which is reconnaissance if
    the endpoint is reachable from outside. Enable it and keep it on an
    internal network, or set `METRICS_TOKEN` and have the scraper send it as a
    bearer token.
    """
    from starlette.responses import PlainTextResponse, Response
    from starlette.routing import Route as StarletteRoute

    try:
        config = app.make("config")
        enabled = bool(config.get("framework.METRICS_ENABLED", False))
        path = str(config.get("framework.METRICS_PATH", "/metrics"))
        token = str(config.get("framework.METRICS_TOKEN", "") or "")
    except Exception:
        return

    if not enabled or path in claimed:
        return

    async def endpoint(request: Any) -> Any:
        if token and not _token_matches(request, token):
            return Response(status_code=404)
        from engine.support.metrics import registry

        body = await _render_metrics(registry)
        return PlainTextResponse(body, media_type="text/plain; version=0.0.4")

    routes.append(StarletteRoute(path, endpoint=endpoint, methods=["GET"]))


def _token_matches(request: Any, expected: str) -> bool:
    """Compare the bearer token without leaking its length through timing.

    A wrong token answers 404 rather than 401: an endpoint that admits it
    exists is an endpoint worth guessing at.
    """
    import hmac

    header = request.headers.get("authorization", "")
    scheme, _, presented = header.partition(" ")
    if scheme.lower() != "bearer":
        return False
    return hmac.compare_digest(presented.strip(), expected)


async def _render_metrics(registry: Any) -> str:
    """Render on a worker thread: the pool gauge issues no query, but a
    registry-wide render walks every series and a custom gauge may block."""
    from starlette.concurrency import run_in_threadpool

    from engine.container.application import Container

    def run() -> str:
        try:
            return registry.render()
        finally:
            try:
                Container.getInstance().make("db").release()
            except Exception:
                pass

    return await run_in_threadpool(run)


async def _run_probe(producer: Callable[[], Tuple[Dict[str, Any], int]]) -> Tuple[Dict[str, Any], int]:
    """Run a probe off the event loop, and release the connection it borrowed.

    The readiness check issues a blocking query, so it belongs on a worker
    thread like every other database call in this framework. The `release()` is
    the same request boundary the kernel applies: without it a probe every ten
    seconds would hold a pooled connection per probing thread forever.
    """
    from starlette.concurrency import run_in_threadpool

    from engine.container.application import Container

    def run() -> Tuple[Dict[str, Any], int]:
        try:
            return producer()
        finally:
            try:
                Container.getInstance().make("db").release()
            except Exception:
                pass

    return await run_in_threadpool(run)
