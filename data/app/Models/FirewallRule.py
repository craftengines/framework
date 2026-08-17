"""FirewallRule Model for Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.orm.model import Model


class FirewallRule(Model):
    __table__ = "firewall_rules"

    fillable = [
        "ip_address",
        "reputation_score",
        "status",
        "blocked_reason",
        "last_event_at",
    ]
