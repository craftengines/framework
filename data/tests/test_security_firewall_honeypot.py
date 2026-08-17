"""
Tests for Web Application Firewall (WAF), Honeypot, and Authentication Cooldown Subsystems.
Category: Core Framework Tests (Security).
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from starlette.requests import Request as StarletteRequest
from starlette.responses import PlainTextResponse

from bootstrap.app import app
from craft.exceptions.handler import AuthorizationException
from craft.facades import Auth, DB, Firewall as FirewallFacade, Honeypot as HoneypotFacade
from craft.http.middleware import AuthenticateApiToken, FirewallMiddleware, SecurityHeaders
from craft.security.firewall import Firewall
from craft.security.honeypot import HoneypotService


def _make_scope(path: str = "/", query_string: bytes = b"", client_ip: str = "127.0.0.1", headers: list = None):
    return {
        "type": "http",
        "method": "GET",
        "path": path,
        "query_string": query_string,
        "headers": headers or [(b"host", b"testserver")],
        "client": (client_ip, 12345),
    }


def test_honeypot_target_detection():
    honeypot = HoneypotService(app)
    assert honeypot.is_honeypot_target("admin") is True
    assert honeypot.is_honeypot_target("root") is True
    assert honeypot.is_honeypot_target("administrator") is True
    assert honeypot.is_honeypot_target("postgres") is True
    assert honeypot.is_honeypot_target("jane.doe@example.com") is False


def test_honeypot_trap_logs_and_blocks():
    honeypot = HoneypotService(app)
    ip = "198.51.100.42"

    result = honeypot.record_attempt(ip=ip, username="root", user_agent="curl/7.68.0")
    assert result["status"] == "HONEYPOT"
    assert result["blocked"] is True

    # Verify audit log and cooldown
    audit_row = DB.table("auth_audit_logs").where("ip_address", ip).where("result", "HONEYPOT").first()
    assert audit_row is not None
    assert audit_row.get("username") == "root"

    is_blocked, blocked_until, _ = honeypot.check_cooldown(ip, "root")
    assert is_blocked is True
    assert blocked_until is not None


def test_brute_force_cooldown_escalation():
    honeypot = HoneypotService(app)
    ip = "203.0.113.10"
    username = "attacker_target"

    # 4 failed attempts should not trigger full cooldown block
    for _ in range(4):
        res = honeypot.record_attempt(ip=ip, username=username, success=False)
        assert res["status"] == "FAILED"
        assert res["blocked"] is False

    # 5th attempt triggers 30-minute cooldown
    res = honeypot.record_attempt(ip=ip, username=username, success=False)
    assert res["status"] == "FAILED"
    assert res["blocked"] is True

    is_blocked, _, reason = honeypot.check_cooldown(ip, username)
    assert is_blocked is True
    assert "Cooldown active" in (reason or "")

    # Successful attempt clears cooldown
    honeypot.record_attempt(ip=ip, username=username, success=True)
    is_blocked_after, _, _ = honeypot.check_cooldown(ip, username)
    assert is_blocked_after is False


def test_firewall_threat_signature_detection():
    fw = Firewall(app)

    # SQL Injection
    assert fw.inspect_payload("SELECT * FROM users WHERE '1'='1'")[0] == "SQL_INJECTION_DETECTED"
    assert fw.inspect_payload("UNION SELECT null, username, password FROM users")[0] == "SQL_INJECTION_DETECTED"

    # XSS
    assert fw.inspect_payload("<script>alert('xss')</script>")[0] == "XSS_INJECTION_DETECTED"
    assert fw.inspect_payload("javascript:document.cookie")[0] == "XSS_INJECTION_DETECTED"

    # Path Traversal
    assert fw.inspect_payload("../../etc/passwd")[0] == "PATH_TRAVERSAL_DETECTED"

    # SSRF
    assert fw.inspect_payload("http://169.254.169.254/latest/meta-data/")[0] == "SSRF_ATTEMPT_DETECTED"

    # Benign string
    assert fw.inspect_payload("/articles/my-first-post?page=2") is None


def test_firewall_whitelist_and_blacklist():
    fw = Firewall(app)
    ip = "192.0.2.55"

    assert fw.is_whitelisted(ip) is False
    assert fw.is_blacklisted(ip) is False

    fw.whitelist_ip(ip)
    assert fw.is_whitelisted(ip) is True
    assert fw.is_blacklisted(ip) is False

    fw.blacklist_ip(ip, reason="Automated bot attack")
    assert fw.is_whitelisted(ip) is False
    assert fw.is_blacklisted(ip) is True


def test_firewall_reputation_auto_blacklisting():
    fw = Firewall(app)
    ip = "198.51.100.99"

    # 1. First threat: 50 points
    is_blacklisted = fw.record_threat(ip, "SQL_INJECTION_DETECTED", 50, "/login", "POST")
    assert is_blacklisted is False
    assert fw.get_reputation_score(ip) == 50

    # 2. Second threat: +50 points => 100 points (threshold reached, auto-blacklist)
    is_blacklisted = fw.record_threat(ip, "SQL_INJECTION_DETECTED", 50, "/login", "POST")
    assert is_blacklisted is True
    assert fw.is_blacklisted(ip) is True
    assert fw.get_reputation_score(ip) == 100


def test_firewall_middleware_blocks_blacklisted_ip():
    fw = Firewall(app)
    ip = "192.0.2.88"
    fw.blacklist_ip(ip, reason="Blacklisted test IP")

    mw = FirewallMiddleware(app)
    request = StarletteRequest(_make_scope(client_ip=ip))

    with pytest.raises(AuthorizationException):
        mw.handle(request, lambda req: PlainTextResponse("OK"))


def test_firewall_middleware_blocks_malicious_query():
    mw = FirewallMiddleware(app)
    scope = _make_scope(path="/search", query_string=b"q=UNION+SELECT+1,2,3--", client_ip="192.0.2.90")
    request = StarletteRequest(scope)

    with pytest.raises(AuthorizationException):
        mw.handle(request, lambda req: PlainTextResponse("OK"))


def test_authenticate_api_token_with_hashed_token():
    from app.Models.User import User

    raw_token = "secret-super-api-token-1234"
    hashed_token = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    user = User.force_create({
        "name": "API Service User",
        "email": "service@craft.local",
        "password": "hashed_pw",
        "api_token": hashed_token,
    })

    mw = AuthenticateApiToken(app)

    # 1. Matching token should authenticate
    headers = [(b"authorization", f"Bearer {raw_token}".encode("utf-8"))]
    request = StarletteRequest(_make_scope(path="/api/data", headers=headers))
    request.bearer_token = lambda: raw_token

    called = []
    response = mw.handle(request, lambda req: (called.append(True), PlainTextResponse("OK"))[1])
    assert len(called) == 1
    assert Auth.user().id == user.id


def test_security_facades_exposed():
    assert FirewallFacade.inspect_payload("<script>alert(1)</script>") is not None
    assert HoneypotFacade.is_honeypot_target("root") is True
