"""Client address resolution behind reverse proxies.

`X-Forwarded-For` is a list the client writes and each proxy only appends to,
so the left-most entry is whatever the client chose. The trustworthy reading
counts from the right, skipping exactly as many hops as there are proxies the
deployment declares. With no declared proxy the header is ignored and the
connection address is the answer.

Category: Core Framework (Security).
Relations:
  - Read by `engine/http/request.py` (`Request.ip`) and
    `engine/security/firewall.py` (`FirewallMiddleware`).
  - Configured by `config/app.py` (`TRUSTED_PROXY_HOPS`).
References:
  - Guide: `documentation/security.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import ipaddress
from typing import Any

#: Returned when no address can be determined. Not routable, so it never
#: matches a real client, yet still usable as a counting key.
UNKNOWN_ADDRESS = "0.0.0.0"


def normalize_ip(candidate: object) -> str | None:
    """Return the canonical form of an IP address, or `None` when invalid.

    `::ffff:203.0.113.7` and `203.0.113.7` are the same client, and a bracketed
    IPv6 literal or an IPv4 address with a port is reduced to the bare address.

    Args:
        candidate: Raw text from a header or the connection.

    Returns:
        The normalized address, or `None` when the text is not an IP.
    """
    text = str(candidate or "").strip()
    if text.startswith("["):
        text = text[1:].split("]")[0]
    elif text.count(":") == 1 and "." in text:
        text = text.split(":")[0]
    try:
        address = ipaddress.ip_address(text)
    except ValueError:
        return None
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        address = address.ipv4_mapped
    return str(address)


def trusted_proxy_hops() -> int:
    """Return how many reverse proxies the deployment declares.

    Reads `app.trusted_proxy_hops`. The legacy boolean `app.trusted_proxies`
    still counts as one hop so existing deployments keep their behaviour.

    Returns:
        The declared hop count; `0` when nothing is declared or config is absent.
    """
    try:
        from engine.container.application import Container

        config = Container.getInstance().make("config")
    except (ImportError, KeyError, LookupError, AttributeError, RuntimeError):
        return 0
    hops = config.get("app.trusted_proxy_hops")
    if hops in (None, ""):
        return 1 if config.get("app.trusted_proxies") else 0
    try:
        return max(int(hops), 0)
    except (TypeError, ValueError):
        return 0


def client_ip(request: Any, hops: int | None = None) -> str:
    """Return the address of the client that made `request`.

    With `hops` proxies in front of the app, the last proxy appends the address
    it received the connection from, so the client sits at position `-hops`.
    A forged prefix never reaches that position. A chain shorter than the
    declared topology falls back to the connection address.

    Args:
        request: Any object exposing `headers` and `client.host`.
        hops: Trusted proxy hops; read from configuration when omitted.

    Returns:
        The client address, or `UNKNOWN_ADDRESS` when none is determinable.
    """
    hops = trusted_proxy_hops() if hops is None else max(hops, 0)
    headers = getattr(request, "headers", None) or {}
    raw = str(headers.get("x-forwarded-for") or "") if hops else ""
    chain = [ip for ip in (normalize_ip(part) for part in raw.split(",")) if ip]
    if hops and len(chain) >= hops:
        return chain[-hops]
    client = getattr(request, "client", None)
    return normalize_ip(getattr(client, "host", None)) or UNKNOWN_ADDRESS
