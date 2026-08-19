"""Domain validation service for decoupling corporate/business rules from operational accounts.

Category: Application (Identity Services).
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from typing import List, Optional
import re


class DomainValidator:
    """Validates email domains against organizational policies without breaking

    administrative, demo, seeding, or operational accounts.
    """

    DEFAULT_SYSTEM_DOMAINS = [
        "craft.local",
        "system.local",
        "test.internal",
        "example.com",
        "example.org",
        "localhost",
    ]

    @classmethod
    def get_allowed_domains(cls) -> List[str]:
        from craft.facades import Config
        try:
            allowed = Config.get("auth.allowed_domains", [])
            return allowed if isinstance(allowed, list) else []
        except Exception:
            return []

    @classmethod
    def get_system_domains(cls) -> List[str]:
        from craft.facades import Config
        try:
            custom_system = Config.get("auth.system_override_domains", cls.DEFAULT_SYSTEM_DOMAINS)
            return custom_system if isinstance(custom_system, list) else cls.DEFAULT_SYSTEM_DOMAINS
        except Exception:
            return cls.DEFAULT_SYSTEM_DOMAINS

    @classmethod
    def extract_domain(cls, email: str) -> Optional[str]:
        if not email or "@" not in email:
            return None
        parts = email.strip().split("@")
        if len(parts) != 2 or not parts[1]:
            return None
        return parts[1].lower()

    @classmethod
    def is_valid_format(cls, email: str) -> bool:
        if not email or not isinstance(email, str):
            return False
        pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        return bool(re.match(pattern, email.strip()))

    @classmethod
    def is_allowed_email(cls, email: str, allow_system_domains: bool = True) -> bool:
        """Check if the given email is permitted under domain validation rules.

        - If no allowed_domains are configured or '*' is in allowed_domains, all valid emails pass.
        - If allowed_domains are defined, matching domains pass.
        - If allow_system_domains is True (default for admin, testing, and operations),
          domains in system_override_domains are always permitted.
        """
        if not cls.is_valid_format(email):
            return False

        domain = cls.extract_domain(email)
        if not domain:
            return False

        allowed = cls.get_allowed_domains()

        # Wildcard / open registration mode
        if not allowed or "*" in allowed:
            return True

        if domain in [d.lower() for d in allowed]:
            return True

        if allow_system_domains:
            system_domains = [d.lower() for d in cls.get_system_domains()]
            if domain in system_domains or domain.endswith(".local") or domain.endswith(".internal"):
                return True

        return False
