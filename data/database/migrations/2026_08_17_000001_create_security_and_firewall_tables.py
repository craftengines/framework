"""
Create security, firewall, honeypot and audit tables migration.
Category: Database Migrations.
"""
from __future__ import annotations

from craft.migrations import Schema


def up() -> None:
    # 1. Authentication Audit Logs Table
    Schema.create_table("auth_audit_logs", lambda t: (
        t.id(),
        t.string("ip_address", max_length=45),
        t.string("username", max_length=255),
        t.text("user_agent").nullable(),
        t.string("result", max_length=20),
        t.string("reason", max_length=100).nullable(),
        t.timestamp("created_at"),
    ))

    # 2. Authentication Cooldowns Table (Brute-force protection)
    Schema.create_table("auth_cooldowns", lambda t: (
        t.id(),
        t.string("identifier_type", max_length=20),  # 'ip' or 'username'
        t.string("identifier_value", max_length=255),
        t.integer("failed_attempts", default=1),
        t.timestamp("blocked_until"),
        t.timestamps(),
    ))

    # 3. Firewall Rules Table (IP Whitelist / Blacklist & Reputation)
    Schema.create_table("firewall_rules", lambda t: (
        t.id(),
        t.string("ip_address", max_length=45).unique(),
        t.integer("reputation_score", default=0),
        t.string("status", max_length=20, default="monitored"),  # 'whitelist', 'blacklist', 'monitored'
        t.string("blocked_reason", max_length=255).nullable(),
        t.timestamp("last_event_at").nullable(),
        t.timestamps(),
    ))

    # 4. Security & IDS Threat Events Table
    Schema.create_table("security_events", lambda t: (
        t.id(),
        t.string("ip_address", max_length=45),
        t.string("event_type", max_length=50),
        t.text("request_uri").nullable(),
        t.string("request_method", max_length=10).nullable(),
        t.text("payload_sample").nullable(),
        t.integer("score_increment", default=10),
        t.timestamp("created_at"),
    ))


def down() -> None:
    Schema.drop_table("security_events")
    Schema.drop_table("firewall_rules")
    Schema.drop_table("auth_cooldowns")
    Schema.drop_table("auth_audit_logs")
