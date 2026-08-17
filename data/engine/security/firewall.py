"""
Web Application Firewall (WAF) & Intrusion Detection System (IDS) for Craft Framework.
Features: IP Whitelist/Blacklist, Anomaly Scoring, SQLi/XSS/SSRF/Traversal Detection.
Category: Core Framework (Security).
Relations:
  - Consumed as `Firewall` facade and `FirewallMiddleware` in `engine/http/middleware.py`.
  - Persists threat logs and reputation to `firewall_rules` and `security_events` tables via `DB`.
References:
  - Guide: `documentation/security.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from starlette.responses import JSONResponse


class Firewall:
    """Core WAF & Threat Intelligence engine."""

    BLACKLIST_THRESHOLD_SCORE: int = 100

    # Threat Signatures (Regular Expressions)
    SQLI_PATTERNS = re.compile(
        r"(\b(UNION(\s+ALL)?|SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|EXEC|EXECUTE)\b|"
        r"['\"]\s*OR\s*['\"]?1['\"]?\s*=\s*['\"]?1|--|\/\*|\*\/|;\s*SHUTDOWN)",
        re.IGNORECASE,
    )
    XSS_PATTERNS = re.compile(
        r"(<script.*?>|javascript:|onload\s*=|onerror\s*=|document\.cookie|<iframe.*?>)",
        re.IGNORECASE,
    )
    TRAVERSAL_PATTERNS = re.compile(
        r"(\.\./|\.\.\\|/etc/passwd|/proc/self|/windows/win\.ini)",
        re.IGNORECASE,
    )
    SSRF_TARGETS = re.compile(
        r"(169\.254\.169\.254|localhost|127\.0\.0\.1|0\.0\.0\.0|internal\.corp)",
        re.IGNORECASE,
    )

    def __init__(self, app: Any = None):
        self.app = app

    def _db(self) -> Any:
        if self.app is not None:
            try:
                return self.app.make("db")
            except Exception:
                pass
        from engine.container.application import Container
        return Container.getInstance().make("db")

    def _format_time(self, dt: datetime) -> str:
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    def whitelist_ip(self, ip: str) -> None:
        """Add an IP to the trusted whitelist (bypasses rate limits and inspection)."""
        now = self._format_time(datetime.now(timezone.utc))
        db = self._db()
        existing = db.table("firewall_rules").where("ip_address", ip).first()
        if existing:
            db.table("firewall_rules").where("ip_address", ip).update({
                "status": "whitelist",
                "reputation_score": 0,
                "blocked_reason": None,
                "updated_at": now,
            })
        else:
            db.table("firewall_rules").insert({
                "ip_address": ip,
                "reputation_score": 0,
                "status": "whitelist",
                "blocked_reason": None,
                "created_at": now,
                "updated_at": now,
            })

    def blacklist_ip(self, ip: str, reason: str = "Manual administrator block") -> None:
        """Add an IP to the permanent blacklist (blocked immediately on all endpoints)."""
        now = self._format_time(datetime.now(timezone.utc))
        db = self._db()
        existing = db.table("firewall_rules").where("ip_address", ip).first()
        if existing:
            db.table("firewall_rules").where("ip_address", ip).update({
                "status": "blacklist",
                "reputation_score": max(int(existing.get("reputation_score") or 0), self.BLACKLIST_THRESHOLD_SCORE),
                "blocked_reason": reason,
                "updated_at": now,
            })
        else:
            db.table("firewall_rules").insert({
                "ip_address": ip,
                "reputation_score": self.BLACKLIST_THRESHOLD_SCORE,
                "status": "blacklist",
                "blocked_reason": reason,
                "created_at": now,
                "updated_at": now,
            })

    def is_whitelisted(self, ip: str) -> bool:
        db = self._db()
        try:
            row = db.table("firewall_rules").where("ip_address", ip).where("status", "whitelist").first()
            return row is not None
        except Exception:
            return False

    def is_blacklisted(self, ip: str) -> bool:
        db = self._db()
        try:
            row = db.table("firewall_rules").where("ip_address", ip).where("status", "blacklist").first()
            return row is not None
        except Exception:
            return False

    def get_reputation_score(self, ip: str) -> int:
        db = self._db()
        try:
            row = db.table("firewall_rules").where("ip_address", ip).first()
            return int(row.get("reputation_score") or 0) if row else 0
        except Exception:
            return 0

    def inspect_payload(self, text: str) -> Optional[Tuple[str, int]]:
        """Inspect text for malicious payload signatures. Returns (threat_type, score_increment)."""
        if not text or not isinstance(text, str):
            return None
        if self.SQLI_PATTERNS.search(text):
            return "SQL_INJECTION_DETECTED", 50
        if self.XSS_PATTERNS.search(text):
            return "XSS_INJECTION_DETECTED", 30
        if self.TRAVERSAL_PATTERNS.search(text):
            return "PATH_TRAVERSAL_DETECTED", 40
        if self.SSRF_TARGETS.search(text):
            return "SSRF_ATTEMPT_DETECTED", 50
        return None

    def record_threat(
        self,
        ip: str,
        threat_type: str,
        score_increment: int,
        uri: str = "",
        method: str = "GET",
        sample: str = "",
    ) -> bool:
        """Record threat event and update IP reputation score. Returns True if IP became blacklisted."""
        now = datetime.now(timezone.utc)
        now_str = self._format_time(now)
        db = self._db()

        try:
            db.table("security_events").insert({
                "ip_address": ip,
                "event_type": threat_type,
                "request_uri": (uri or "")[:500],
                "request_method": (method or "GET")[:10],
                "payload_sample": (sample or "")[:1000],
                "score_increment": score_increment,
                "created_at": now_str,
            })
        except Exception:
            pass

        try:
            existing = db.table("firewall_rules").where("ip_address", ip).first()
            current_score = (int(existing.get("reputation_score") or 0) + score_increment) if existing else score_increment
            new_status = "blacklist" if current_score >= self.BLACKLIST_THRESHOLD_SCORE else (
                existing.get("status", "monitored") if existing else "monitored"
            )

            if existing:
                db.table("firewall_rules").where("ip_address", ip).update({
                    "reputation_score": current_score,
                    "status": new_status,
                    "blocked_reason": threat_type if new_status == "blacklist" else existing.get("blocked_reason"),
                    "last_event_at": now_str,
                    "updated_at": now_str,
                })
            else:
                db.table("firewall_rules").insert({
                    "ip_address": ip,
                    "reputation_score": current_score,
                    "status": new_status,
                    "blocked_reason": threat_type if new_status == "blacklist" else None,
                    "last_event_at": now_str,
                    "created_at": now_str,
                    "updated_at": now_str,
                })

            return new_status == "blacklist"
        except Exception:
            return False


class FirewallMiddleware:
    """Synchronous middleware that inspects requests against WAF and reputation rules."""

    def __init__(self, app: Any = None):
        self.app = app
        self._firewall = Firewall(app)

    def _extract_ip(self, request: Any) -> str:
        forwarded = getattr(request, "headers", {}).get("x-forwarded-for")
        if forwarded:
            return str(forwarded).split(",")[0].strip()
        client = getattr(request, "client", None)
        return getattr(client, "host", None) or "127.0.0.1"

    def handle(self, request: Any, next_callable: Callable) -> Any:
        ip = self._extract_ip(request)

        # 1. Check IP Whitelist / Blacklist
        if self._firewall.is_whitelisted(ip):
            return next_callable(request)

        if self._firewall.is_blacklisted(ip):
            from engine.exceptions.handler import AuthorizationException
            if getattr(request, "expects_json", lambda: False)():
                return JSONResponse(
                    {"error": "Access denied by firewall security policy.", "code": "IP_BLACKLISTED"},
                    status_code=403,
                )
            raise AuthorizationException("Access denied by firewall security policy.")

        # 2. Inspect URI and Query String for threat signatures
        url_path = str(getattr(getattr(request, "url", None), "path", ""))
        query_string = str(getattr(getattr(request, "url", None), "query", ""))
        sample = f"{url_path} ? {query_string}"

        threat = self._firewall.inspect_payload(sample)
        if threat:
            threat_type, score_inc = threat
            method = getattr(request, "method", "GET")
            self._firewall.record_threat(
                ip=ip,
                threat_type=threat_type,
                score_increment=score_inc,
                uri=url_path,
                method=method,
                sample=sample,
            )

            from engine.exceptions.handler import AuthorizationException
            if getattr(request, "expects_json", lambda: False)():
                return JSONResponse(
                    {"error": "Malicious payload signature detected.", "incident_ref": threat_type},
                    status_code=403,
                )
            raise AuthorizationException(f"Malicious payload signature detected: {threat_type}")

        return next_callable(request)


__all__ = ["Firewall", "FirewallMiddleware"]
