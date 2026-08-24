"""
Honeypot, Authentication Audit & Brute-force Cooldown Subsystem.
Category: Core Framework (Security).
Relations:
  - Consumed by `engine/auth/manager.py` and security middlewares.
  - Interacts with `auth_audit_logs`, `auth_cooldowns` and `security_events` tables via `DB`.
References:
  - Guide: `documentation/security.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple


class HoneypotService:
    """Detects and neutralizes malicious login attempts, maintaining audit trails and cooldowns."""

    #: Commonly targeted administrative accounts trapped on login attempts.
    ABUSED_USERNAMES: Set[str] = {
        "admin", "administrator", "root", "system", "test", "guest",
        "user", "manager", "support", "webmaster", "superuser",
        "operator", "postgres", "dbadmin", "master", "default"
    }

    MAX_FAILED_ATTEMPTS: int = 5
    COOLDOWN_MINUTES: int = 30

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

    def is_honeypot_target(self, username: str) -> bool:
        """Check whether the given username matches a known honeypot trap target."""
        if not username or not isinstance(username, str):
            return False
        clean = username.strip().lower()
        return clean in self.ABUSED_USERNAMES

    def _format_time(self, dt: datetime) -> str:
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    def _parse_time(self, val: Any) -> Optional[datetime]:
        if isinstance(val, datetime):
            return val if val.tzinfo is not None else val.replace(tzinfo=timezone.utc)
        if isinstance(val, str):
            for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
                try:
                    parsed = datetime.strptime(val.rstrip("Z"), fmt)
                    return parsed.replace(tzinfo=timezone.utc)
                except ValueError:
                    pass
        return None

    def check_cooldown(self, ip: str, username: str) -> Tuple[bool, Optional[datetime], Optional[str]]:
        """Verify if an IP address or username is currently blocked under a cooldown period.
        
        Returns: (is_blocked, blocked_until, reason)
        """
        now = datetime.now(timezone.utc)
        clean_user = (username or "").strip().lower()

        db = self._db()
        try:
            records = db.table("auth_cooldowns") \
                .where_in("identifier_value", [ip, clean_user]) \
                .get()
        except Exception:
            return False, None, None

        for rec in records:
            blocked_until = self._parse_time(rec.get("blocked_until"))
            if blocked_until and blocked_until > now:
                reason = f"Too many failed login attempts for {rec.get('identifier_type')}. Cooldown active."
                return True, blocked_until, reason

        return False, None, None

    def record_attempt(
        self,
        ip: str,
        username: str,
        user_agent: Optional[str] = None,
        success: bool = False,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record login attempt, update cooldowns, and trigger honeypot alerts if applicable."""
        now = datetime.now(timezone.utc)
        now_str = self._format_time(now)
        clean_user = (username or "empty").strip().lower()
        ua_string = (user_agent or "")[:500]
        db = self._db()

        # 1. Honeypot Trap Trigger
        if self.is_honeypot_target(clean_user):
            try:
                db.table("auth_audit_logs").insert({
                    "ip_address": ip,
                    "username": clean_user,
                    "user_agent": ua_string,
                    "result": "HONEYPOT",
                    "reason": "ABUSED_USERNAME_TRAP",
                    "created_at": now_str,
                })
                db.table("security_events").insert({
                    "ip_address": ip,
                    "event_type": "HONEYPOT_HIT",
                    "request_uri": "/login",
                    "request_method": "POST",
                    "payload_sample": f"Trapped username: {clean_user}",
                    "score_increment": 40,
                    "created_at": now_str,
                })
                # Enforce immediate 30-minute block on the attacking IP
                blocked_until = self._format_time(now + timedelta(minutes=self.COOLDOWN_MINUTES))
                self._upsert_cooldown(ip, "ip", self.MAX_FAILED_ATTEMPTS, blocked_until, now_str)
            except Exception:
                pass
            return {"status": "HONEYPOT", "blocked": True, "reason": "ABUSED_USERNAME_TRAP"}

        # 2. Regular Authentication Audit Log
        result_status = "SUCCESS" if success else "FAILED"
        final_reason = reason or ("AUTHENTICATED" if success else "INVALID_CREDENTIALS")

        try:
            db.table("auth_audit_logs").insert({
                "ip_address": ip,
                "username": clean_user,
                "user_agent": ua_string,
                "result": result_status,
                "reason": final_reason,
                "created_at": now_str,
            })
        except Exception:
            pass

        if success:
            # Clear previous failed attempts
            try:
                db.table("auth_cooldowns").where("identifier_value", ip).delete()
                db.table("auth_cooldowns").where("identifier_value", clean_user).delete()
            except Exception:
                pass
            return {"status": "SUCCESS", "blocked": False, "reason": final_reason}

        # 3. Failed Attempt Cooldown Tracking
        blocked = False
        for id_val, id_type in [(ip, "ip"), (clean_user, "username")]:
            if not id_val or id_val == "empty":
                continue
            try:
                existing = db.table("auth_cooldowns") \
                    .where("identifier_type", id_type) \
                    .where("identifier_value", id_val) \
                    .first()

                attempts = (int(existing.get("failed_attempts") or 0) + 1) if existing else 1
                if attempts >= self.MAX_FAILED_ATTEMPTS:
                    blocked = True
                    blocked_until = self._format_time(now + timedelta(minutes=self.COOLDOWN_MINUTES))
                else:
                    blocked_until = now_str

                self._upsert_cooldown(id_val, id_type, attempts, blocked_until, now_str)
            except Exception:
                pass

        return {"status": "FAILED", "blocked": blocked, "reason": final_reason}

    def _upsert_cooldown(
        self,
        identifier_value: str,
        identifier_type: str,
        attempts: int,
        blocked_until: str,
        now_str: str,
    ) -> None:
        db = self._db()
        existing = db.table("auth_cooldowns") \
            .where("identifier_type", identifier_type) \
            .where("identifier_value", identifier_value) \
            .first()

        if existing:
            db.table("auth_cooldowns") \
                .where("identifier_type", identifier_type) \
                .where("identifier_value", identifier_value) \
                .update({
                    "failed_attempts": attempts,
                    "blocked_until": blocked_until,
                    "updated_at": now_str,
                })
        else:
            db.table("auth_cooldowns").insert({
                "identifier_type": identifier_type,
                "identifier_value": identifier_value,
                "failed_attempts": attempts,
                "blocked_until": blocked_until,
                "created_at": now_str,
                "updated_at": now_str,
            })


__all__ = ["HoneypotService"]
