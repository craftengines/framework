"""AuthAuditLog Model for Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.orm.model import Model


class AuthAuditLog(Model):
    __table__ = "auth_audit_logs"

    fillable = [
        "ip_address",
        "username",
        "user_agent",
        "result",
        "reason",
        "created_at",
    ]
