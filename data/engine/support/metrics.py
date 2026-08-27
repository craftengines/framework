"""In-process metrics, exposed in the Prometheus text format.

Deliberately a registry in memory rather than a client library: the numbers a
scrape needs are counters and one latency histogram, the format is a documented
line protocol, and a dependency that pulls in its own multiprocess coordination
would be a larger commitment than the thing it measures.

The scope is one process. Each worker is scraped separately and the numbers are
summed by whatever collects them, which is how the format is meant to be used
and is also the only honest answer: a counter shared between processes would
need shared memory this framework does not otherwise require.

Category: Core Framework (Support).
Relations:
  - Recorded by `RequestContext` middleware in `engine/http/middleware.py`.
  - Rendered by the `/metrics` route mounted in `engine/http/health.py`.
References:
  - Guide: `documentation/observability.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import threading
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

#: Request latency buckets in seconds. Chosen around the boundaries a decision
#: is actually made at: the 100ms that separates fast from noticeable, the 1s
#: a user starts waiting at, and the 10s beyond which the answer no longer
#: matters. Cumulative, as the format requires.
DEFAULT_BUCKETS: Tuple[float, ...] = (
    0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0,
)

#: Label values go into the exposition format unquoted-ish, and a series is
#: created per distinct combination. Both are reasons to bound them.
_ESCAPES = ((chr(92), chr(92) * 2), ('"', chr(92) + '"'), ("\n", chr(92) + "n"))

Labels = Tuple[Tuple[str, str], ...]


def _normalize(labels: Optional[Dict[str, Any]]) -> Labels:
    if not labels:
        return ()
    return tuple(sorted((str(k), str(v)) for k, v in labels.items()))


def _escape(value: str) -> str:
    for old, new in _ESCAPES:
        value = value.replace(old, new)
    return value


def _render_labels(labels: Labels, extra: Optional[Tuple[str, str]] = None) -> str:
    pairs = list(labels)
    if extra is not None:
        pairs.append(extra)
    if not pairs:
        return ""
    inner = ",".join(f'{name}="{_escape(value)}"' for name, value in pairs)
    return "{" + inner + "}"


class Counter:
    """A value that only goes up, per label combination."""

    kind = "counter"

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self._values: Dict[Labels, float] = {}

    def increment(self, amount: float = 1.0, **labels: Any) -> None:
        key = _normalize(labels)
        self._values[key] = self._values.get(key, 0.0) + amount

    def value(self, **labels: Any) -> float:
        return self._values.get(_normalize(labels), 0.0)

    def samples(self) -> Iterable[str]:
        for labels, value in sorted(self._values.items()):
            yield f"{self.name}{_render_labels(labels)} {_format(value)}"


class Gauge:
    """A value read at scrape time rather than accumulated.

    Backed by a callable because the interesting gauges - pool occupancy,
    queue depth - are already tracked by whatever owns them, and a copy kept
    in step by hand would be a second source of truth that drifts.
    """

    kind = "gauge"

    def __init__(self, name: str, description: str, reader: Callable[[], Any]):
        self.name = name
        self.description = description
        self.reader = reader

    def samples(self) -> Iterable[str]:
        """One line, or one per label combination when the reader returns a map.

        A reader that raises yields nothing rather than failing the scrape: the
        remaining numbers are exactly what an operator wants at the moment a
        dependency is unavailable.
        """
        try:
            reading = self.reader()
        except Exception:
            return
        if not isinstance(reading, dict):
            yield f"{self.name} {_format(reading)}"
            return
        for labels, value in sorted(reading.items()):
            yield f"{self.name}{_render_labels(tuple(labels))} {_format(value)}"


class Histogram:
    """Cumulative buckets, a sum and a count, per label combination."""

    kind = "histogram"

    def __init__(self, name: str, description: str, buckets: Tuple[float, ...] = DEFAULT_BUCKETS):
        self.name = name
        self.description = description
        self.buckets = tuple(sorted(buckets))
        self._counts: Dict[Labels, List[int]] = {}
        self._sums: Dict[Labels, float] = {}
        self._totals: Dict[Labels, int] = {}

    def observe(self, value: float, **labels: Any) -> None:
        key = _normalize(labels)
        counts = self._counts.setdefault(key, [0] * len(self.buckets))
        for index, edge in enumerate(self.buckets):
            if value <= edge:
                counts[index] += 1
        self._sums[key] = self._sums.get(key, 0.0) + value
        self._totals[key] = self._totals.get(key, 0) + 1

    def count(self, **labels: Any) -> int:
        return self._totals.get(_normalize(labels), 0)

    def samples(self) -> Iterable[str]:
        for labels in sorted(self._counts):
            counts = self._counts[labels]
            for edge, count in zip(self.buckets, counts, strict=True):
                rendered = _render_labels(labels, ("le", _format(edge)))
                yield f"{self.name}_bucket{rendered} {count}"
            total = self._totals[labels]
            yield f"{self.name}_bucket{_render_labels(labels, ('le', '+Inf'))} {total}"
            yield f"{self.name}_sum{_render_labels(labels)} {_format(self._sums[labels])}"
            yield f"{self.name}_count{_render_labels(labels)} {total}"


def _format(value: Any) -> str:
    """Render a number the way the exposition format expects it."""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    number = float(value)
    if number.is_integer() and abs(number) < 1e15:
        return str(int(number))
    return repr(number)


class MetricsRegistry:
    """Every metric this process reports.

    One lock around mutation. The alternative - a lock-free counter per label
    combination - buys nothing here: the recorded work is a dictionary update
    per request, several orders of magnitude below the request it describes.
    """

    def __init__(self) -> None:
        # Reentrant: `increment` declares the metric it is about to record on,
        # and both steps belong inside one critical section.
        self._lock = threading.RLock()
        self._metrics: Dict[str, Any] = {}
        self.enabled = True

    # -- declaration -----------------------------------------------------------

    def counter(self, name: str, description: str = "") -> Counter:
        with self._lock:
            existing = self._metrics.get(name)
            if existing is None:
                existing = Counter(name, description)
                self._metrics[name] = existing
            return existing

    def histogram(
        self, name: str, description: str = "", buckets: Tuple[float, ...] = DEFAULT_BUCKETS
    ) -> Histogram:
        with self._lock:
            existing = self._metrics.get(name)
            if existing is None:
                existing = Histogram(name, description, buckets)
                self._metrics[name] = existing
            return existing

    def gauge(self, name: str, description: str, reader: Callable[[], Any]) -> Gauge:
        with self._lock:
            gauge = Gauge(name, description, reader)
            self._metrics[name] = gauge
            return gauge

    # -- recording -------------------------------------------------------------

    def increment(self, name: str, amount: float = 1.0, **labels: Any) -> None:
        if not self.enabled:
            return
        with self._lock:
            self.counter(name).increment(amount, **labels)

    def observe(self, name: str, value: float, **labels: Any) -> None:
        if not self.enabled:
            return
        with self._lock:
            self.histogram(name).observe(value, **labels)

    def get(self, name: str) -> Any:
        return self._metrics.get(name)

    def reset(self) -> None:
        """Drop every recorded value. For tests, never for a running process."""
        with self._lock:
            self._metrics.clear()

    # -- exposition ------------------------------------------------------------

    def render(self) -> str:
        """The whole registry in the Prometheus text exposition format."""
        with self._lock:
            metrics = list(self._metrics.values())

        lines: List[str] = []
        for metric in metrics:
            samples = list(metric.samples())
            if not samples:
                continue
            if metric.description:
                lines.append(f"# HELP {metric.name} {metric.description}")
            lines.append(f"# TYPE {metric.name} {metric.kind}")
            lines.extend(samples)
        return "\n".join(lines) + "\n"


#: The process-wide registry. A module-level singleton on purpose: metrics are
#: a property of the process, and threading one through every call site that
#: might record something would be a large change for no gain in clarity.
registry = MetricsRegistry()


def register_default_metrics(app: Any) -> None:
    """Declare the metrics the framework itself reports.

    Called once at startup. The gauges read through the container lazily, so a
    scrape never boots a service that the request path has not booted, and a
    service that is unavailable leaves its gauge out of the response instead
    of failing the whole scrape.
    """
    registry.counter(
        "craft_requests_total", "HTTP requests handled, by method, route and status."
    )
    registry.counter(
        "craft_exceptions_total", "Unhandled exceptions, by exception class."
    )
    registry.histogram(
        "craft_request_duration_seconds", "HTTP request duration in seconds."
    )
    registry.gauge(
        "craft_db_pool_connections",
        "Physical database connections, by connection and state.",
        lambda: _pool_readings(app),
    )


def _pool_readings(app: Any) -> Dict[Any, Any]:
    """Pool occupancy per configured connection.

    `open == size` sustained is the shape of a connection leak, and it is
    visible here before it is visible in the error rate.
    """
    readings: Dict[Any, Any] = {}
    db = app.make("db")
    for name, connection in (("write", db.write_connection), ("read", db.read_connection)):
        if connection is None:
            continue
        stats = connection.pool_stats
        readings[(("connection", name), ("state", "open"))] = stats["open"]
        readings[(("connection", name), ("state", "idle"))] = stats["idle"]
        readings[(("connection", name), ("state", "limit"))] = connection.pool_size
    return readings
