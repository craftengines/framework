"""
AntiSpam — Form honeypots, cryptographic time-traps and heuristic spam protection.
Category: Core Framework (Security).
Relations:
  - Bound as `antispam`, exposed via the `AntiSpam` facade.
  - Consumed by `engine/validation/validator.py`, `engine/validation/form_request.py`,
    and `engine/view/forge.py`.
  - Records events into `security_events` table via DB.
References:
  - Guide: `documentation/security.md#antispam-protection`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple


class SpamDetectedException(Exception):
    """Raised when an automated bot or spam submission is trapped."""

    status_code = 422

    def __init__(self, reason: str = "Spam detected", errors: Optional[Dict[str, List[str]]] = None):
        self.reason = reason
        self.errors = errors or {"_antispam": [reason]}
        super().__init__(reason)


class AntiSpamService:
    """Enterprise-grade anti-spam subsystem combining honeypots, time-traps, and content heuristics."""

    DEFAULT_HONEYPOT_FIELD = "_craft_hp_name"
    DEFAULT_TIME_FIELD = "_craft_hp_time"
    DEFAULT_MIN_SECONDS = 2.0
    DEFAULT_MAX_SECONDS = 86400.0  # 24 hours

    #: High-confidence spam trigger keywords (matched case-insensitively).
    SPAM_PATTERNS: List[re.Pattern] = [
        re.compile(r"\b(casino|viagra|cialis|poker|cryptocurrency\s+giveaway|telegram\s*:\s*@)\b", re.IGNORECASE),
        re.compile(r"\[url=https?://.+?\]", re.IGNORECASE),
        re.compile(r"<a\s+href=[\"']https?://.+?[\"']", re.IGNORECASE),
        re.compile(r"\b(whatsapp\s*:\s*\+\d{8,})\b", re.IGNORECASE),
    ]

    #: Known disposable/temporary email provider domains commonly used by spam bots.
    DISPOSABLE_EMAIL_DOMAINS: Set[str] = {
        "tempmail.com", "guerrillamail.com", "10minutemail.com", "mailinator.com",
        "throwawaymail.com", "yopmail.com", "trashmail.com", "sharklasers.com",
    }

    def __init__(self, app: Any = None):
        self.app = app

    def _config(self) -> Any:
        if self.app is not None:
            try:
                return self.app.make("config")
            except Exception:
                pass
        from engine.container.application import Container
        try:
            return Container.getInstance().make("config")
        except Exception:
            return None

    def _db(self) -> Any:
        if self.app is not None:
            try:
                return self.app.make("db")
            except Exception:
                pass
        from engine.container.application import Container
        try:
            return Container.getInstance().make("db")
        except Exception:
            return None

    def _app_key(self) -> str:
        cfg = self._config()
        if cfg:
            key = cfg.get("app.APP_KEY") or cfg.get("app.app_key")
            if key:
                return str(key)
        return os.environ.get("APP_KEY", "craft-engine-fallback-antispam-secret-key-3.19")

    # -- Honeypot & Time Token Generation --------------------------------------

    def generate_time_token(self, action: str = "") -> str:
        """Create a tamper-evident, HMAC-signed timestamp token."""
        timestamp = int(time.time())
        clean_action = str(action or "").strip().lower()
        payload = f"{timestamp}:{clean_action}"
        key = self._app_key().encode("utf-8")
        signature = hmac.new(key, payload.encode("utf-8"), hashlib.sha256).hexdigest()
        raw = f"{payload}:{signature}"
        return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8")

    def verify_time_token(
        self,
        token: str,
        action: str = "",
        min_seconds: Optional[float] = None,
        max_seconds: Optional[float] = None,
    ) -> Tuple[bool, str]:
        """Verify the validity, age, and integrity of a timestamp token.

        Returns:
            Tuple of (is_valid, reason_code)
        """
        if not token or not isinstance(token, str):
            return False, "TOKEN_MISSING"

        try:
            decoded = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
            parts = decoded.split(":")
            if len(parts) != 3:
                return False, "TOKEN_MALFORMED"

            raw_ts, token_action, signature = parts
            timestamp = int(raw_ts)
        except Exception:
            return False, "TOKEN_INVALID"

        expected_action = str(action or "").strip().lower()
        if token_action != expected_action:
            return False, "ACTION_MISMATCH"

        payload = f"{timestamp}:{token_action}"
        key = self._app_key().encode("utf-8")
        expected_sig = hmac.new(key, payload.encode("utf-8"), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(expected_sig, signature):
            return False, "SIGNATURE_MISMATCH"

        now = time.time()
        elapsed = now - timestamp

        min_sec = min_seconds if min_seconds is not None else self.DEFAULT_MIN_SECONDS
        max_sec = max_seconds if max_seconds is not None else self.DEFAULT_MAX_SECONDS

        if elapsed < min_sec:
            return False, "SUBMITTED_TOO_FAST"
        if elapsed > max_sec:
            return False, "TOKEN_EXPIRED"

        return True, "OK"

    def generate_fields(
        self,
        field_name: Optional[str] = None,
        time_field: Optional[str] = None,
        action: str = "",
    ) -> str:
        """Render invisible honeypot and time-trap fields for HTML forms.

        Screen-reader accessible attributes (tabindex=-1, aria-hidden=true, autocomplete=new-password)
        prevent legitimate users and autofill tools from touching the trap while trapping automated bots.
        """
        hp_field = field_name or self.DEFAULT_HONEYPOT_FIELD
        tp_field = time_field or self.DEFAULT_TIME_FIELD
        token = self.generate_time_token(action=action)

        return (
            f'<div class="craft-hp-wrapper" '
            f'style="display:none!important;position:absolute!important;left:-9999px!important;'
            f'top:-9999px!important;opacity:0!important;pointer-events:none!important;" '
            f'aria-hidden="true">\n'
            f'    <label for="{hp_field}">Do not fill this field</label>\n'
            f'    <input type="text" name="{hp_field}" id="{hp_field}" value="" '
            f'tabindex="-1" autocomplete="new-password" />\n'
            f'    <input type="hidden" name="{tp_field}" value="{token}" />\n'
            f'</div>'
        )

    # -- Content Heuristics ----------------------------------------------------

    def analyze_content(self, data: Dict[str, Any]) -> Tuple[float, List[str]]:
        """Score payload text fields for common automated spam indicators.

        Returns:
            Tuple of (spam_score: float [0.0..1.0], reasons: List[str])
        """
        score = 0.0
        reasons: List[str] = []

        all_text_parts: List[str] = []
        for key, val in data.items():
            if key.startswith("_"):
                continue
            if isinstance(val, str):
                all_text_parts.append(val)
                # Check for disposable email
                if "@" in val:
                    domain = val.split("@", 1)[1].strip().lower()
                    if domain in self.DISPOSABLE_EMAIL_DOMAINS:
                        score += 0.6
                        reasons.append(f"DISPOSABLE_EMAIL:{domain}")

        combined_text = " ".join(all_text_parts)
        if not combined_text.strip():
            return score, reasons

        # 1. Spam regex triggers
        for pattern in self.SPAM_PATTERNS:
            if pattern.search(combined_text):
                score += 0.5
                reasons.append(f"SPAM_PATTERN_HIT:{pattern.pattern[:30]}")

        # 2. Excessive hyperlink density
        urls = re.findall(r"https?://[^\s]+", combined_text, re.IGNORECASE)
        words = re.findall(r"\b\w+\b", combined_text)
        if words and urls:
            url_density = len(urls) / max(len(words), 1)
            if len(urls) >= 3 or url_density > 0.35:
                score += 0.4
                reasons.append(f"HIGH_URL_DENSITY:{len(urls)}_urls")

        return min(score, 1.0), reasons

    # -- Verification & Audit --------------------------------------------------

    def extract_data(self, request_or_data: Any) -> Dict[str, Any]:
        """Normalise input from dict or Starlette/Craft Request."""
        if isinstance(request_or_data, dict):
            return dict(request_or_data)
        if hasattr(request_or_data, "all"):
            try:
                return dict(request_or_data.all() or {})
            except Exception:
                pass
        if hasattr(request_or_data, "_form") and isinstance(request_or_data._form, dict):
            return dict(request_or_data._form)
        return {}

    def extract_ip(self, request_or_data: Any) -> str:
        if hasattr(request_or_data, "client") and request_or_data.client:
            return getattr(request_or_data.client, "host", "127.0.0.1")
        if hasattr(request_or_data, "ip"):
            try:
                return str(request_or_data.ip())
            except Exception:
                pass
        return "127.0.0.1"

    def extract_uri(self, request_or_data: Any) -> str:
        if hasattr(request_or_data, "url"):
            return str(getattr(request_or_data.url, "path", "/form"))
        return "/form"

    def record_spam_event(
        self,
        ip: str,
        uri: str,
        reason: str,
        sample: str = "",
        score_increment: int = 35,
    ) -> None:
        """Persist detection into the security_events audit table."""
        db = self._db()
        if db is None:
            return
        now_str = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        try:
            db.table("security_events").insert({
                "ip_address": ip,
                "event_type": "FORM_SPAM_TRAP",
                "request_uri": uri[:255],
                "request_method": "POST",
                "payload_sample": f"{reason} | {sample}"[:500],
                "score_increment": score_increment,
                "created_at": now_str,
            })
        except Exception:
            # Audit logging failure must never crash request handling
            pass

    def verify(
        self,
        request_or_data: Any,
        action: str = "",
        field_name: Optional[str] = None,
        time_field: Optional[str] = None,
        check_content: bool = True,
        content_threshold: float = 0.7,
    ) -> Tuple[bool, str]:
        """Perform comprehensive anti-spam check on form submission.

        Returns:
            Tuple of (is_clean: bool, reason_code: str)
        """
        data = self.extract_data(request_or_data)
        hp_field = field_name or self.DEFAULT_HONEYPOT_FIELD
        tp_field = time_field or self.DEFAULT_TIME_FIELD

        # 1. Check honeypot trap field (must be empty or omitted)
        trap_value = str(data.get(hp_field, "")).strip()
        if trap_value:
            ip = self.extract_ip(request_or_data)
            uri = self.extract_uri(request_or_data)
            self.record_spam_event(ip, uri, "HONEYPOT_FILLED", sample=f"field={hp_field}, val={trap_value[:50]}")
            return False, "HONEYPOT_FILLED"

        # 2. Check time token if present in form payload
        if tp_field in data:
            token = str(data.get(tp_field, "")).strip()
            valid_time, time_reason = self.verify_time_token(token, action=action)
            if not valid_time:
                ip = self.extract_ip(request_or_data)
                uri = self.extract_uri(request_or_data)
                self.record_spam_event(ip, uri, f"TIME_TRAP:{time_reason}")
                return False, f"TIME_TRAP_{time_reason}"

        # 3. Content heuristics check
        if check_content:
            score, reasons = self.analyze_content(data)
            if score >= content_threshold:
                ip = self.extract_ip(request_or_data)
                uri = self.extract_uri(request_or_data)
                self.record_spam_event(ip, uri, "CONTENT_HEURISTIC_SPAM", sample=",".join(reasons))
                return False, "CONTENT_SPAM_SCORE_EXCEEDED"

        return True, "OK"

    def validate(
        self,
        request_or_data: Any,
        action: str = "",
        field_name: Optional[str] = None,
        time_field: Optional[str] = None,
        check_content: bool = True,
    ) -> None:
        """Verify anti-spam rules and raise SpamDetectedException on detection."""
        is_clean, reason = self.verify(
            request_or_data,
            action=action,
            field_name=field_name,
            time_field=time_field,
            check_content=check_content,
        )
        if not is_clean:
            raise SpamDetectedException(
                reason=f"Form submission rejected by anti-spam trap ({reason}).",
                errors={"_antispam": [f"Submission rejected: {reason}"]},
            )


__all__ = ["AntiSpamService", "SpamDetectedException"]
