"""SecurityEvent Model for Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.orm.model import Model


class SecurityEvent(Model):
    __table__ = "security_events"

    fillable = [
        "ip_address",
        "event_type",
        "request_uri",
        "request_method",
        "payload_sample",
        "score_increment",
        "created_at",
    ]
