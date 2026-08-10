"""Minimal throughput probe: does concurrency actually buy anything?

The point is not an absolute number — it is the *shape*. A process that serves
one request at a time gives the same requests/second at 1 client and at 50; a
process that overlaps them does not. Run it against a booted server:

    python tools/loadtest.py http://127.0.0.1:8000/ --clients 1 --clients 20

Standard library only, so it runs anywhere the framework does.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import argparse
import statistics
import threading
import time
import urllib.error
import urllib.request


def _worker(url: str, deadline: float, latencies: list, failures: list) -> None:
    while time.monotonic() < deadline:
        started = time.monotonic()
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                response.read()
        except (urllib.error.URLError, OSError) as exc:
            failures.append(repr(exc))
            continue
        latencies.append(time.monotonic() - started)


def run(url: str, clients: int, seconds: float) -> dict:
    latencies: list = []
    failures: list = []
    deadline = time.monotonic() + seconds

    threads = [
        threading.Thread(target=_worker, args=(url, deadline, latencies, failures))
        for _ in range(clients)
    ]
    started = time.monotonic()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.monotonic() - started

    ordered = sorted(latencies)
    return {
        "clients": clients,
        "requests": len(latencies),
        "failures": len(failures),
        "seconds": elapsed,
        "rps": len(latencies) / elapsed if elapsed else 0.0,
        "median_ms": statistics.median(ordered) * 1000 if ordered else 0.0,
        "p95_ms": ordered[int(len(ordered) * 0.95)] * 1000 if ordered else 0.0,
        "first_failure": failures[0] if failures else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument(
        "--clients", type=int, action="append", default=None,
        help="Concurrency level; repeat the flag to sweep several.",
    )
    parser.add_argument("--seconds", type=float, default=5.0)
    args = parser.parse_args()

    levels = args.clients or [1, 10, 50]
    print(f"{'clients':>8} {'req/s':>9} {'median':>9} {'p95':>9} {'reqs':>7} {'fail':>6}")
    for clients in levels:
        result = run(args.url, clients, args.seconds)
        print(
            f"{result['clients']:>8} {result['rps']:>9.1f} "
            f"{result['median_ms']:>8.0f}ms {result['p95_ms']:>8.0f}ms "
            f"{result['requests']:>7} {result['failures']:>6}"
        )
        if result["first_failure"]:
            print(f"         first failure: {result['first_failure']}")


if __name__ == "__main__":
    main()
