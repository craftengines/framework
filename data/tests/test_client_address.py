"""Client address resolution: a forged X-Forwarded-For prefix is never trusted."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from types import SimpleNamespace

import pytest

from craft.security.firewall import FirewallMiddleware
from craft.security.net import UNKNOWN_ADDRESS, client_ip, normalize_ip


def _request(forwarded: str | None = None, host: str | None = "198.51.100.9") -> SimpleNamespace:
    headers = {"x-forwarded-for": forwarded} if forwarded is not None else {}
    client = SimpleNamespace(host=host) if host is not None else None
    return SimpleNamespace(headers=headers, client=client)


def test_without_declared_proxy_the_forwarded_header_is_ignored() -> None:
    assert client_ip(_request("6.6.6.6"), hops=0) == "198.51.100.9"


def test_forged_prefix_is_skipped_with_one_proxy() -> None:
    assert client_ip(_request("6.6.6.6, 203.0.113.7"), hops=1) == "203.0.113.7"


def test_client_sits_at_minus_hops_with_two_proxies() -> None:
    assert client_ip(_request("6.6.6.6, 203.0.113.7, 10.0.0.2"), hops=2) == "203.0.113.7"


def test_chain_shorter_than_topology_falls_back_to_connection() -> None:
    assert client_ip(_request("203.0.113.7"), hops=2) == "198.51.100.9"


def test_invalid_entries_are_discarded() -> None:
    assert client_ip(_request("garbage, 203.0.113.7"), hops=1) == "203.0.113.7"


def test_nothing_determinable_returns_unknown_address() -> None:
    assert client_ip(_request(host=None), hops=1) == UNKNOWN_ADDRESS


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("::ffff:203.0.113.7", "203.0.113.7"),
        ("[::1]:443", "::1"),
        ("203.0.113.7:8080", "203.0.113.7"),
        ("not-an-ip", None),
        ("", None),
    ],
)
def test_normalize_ip(raw: str, expected: str | None) -> None:
    assert normalize_ip(raw) == expected


def test_firewall_does_not_take_the_client_chosen_address(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("engine.security.net.trusted_proxy_hops", lambda: 1)
    middleware = FirewallMiddleware.__new__(FirewallMiddleware)
    assert middleware._extract_ip(_request("6.6.6.6, 203.0.113.7")) == "203.0.113.7"


def test_firewall_ignores_the_header_when_no_proxy_is_declared(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("engine.security.net.trusted_proxy_hops", lambda: 0)
    middleware = FirewallMiddleware.__new__(FirewallMiddleware)
    assert middleware._extract_ip(_request("6.6.6.6")) == "198.51.100.9"
