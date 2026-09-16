"""Web Application Firewall configuration."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.config import env

#: Log and score threats as usual, but never block or blacklist - for rolling
#: out a new signature/threshold and watching what it *would* have done
#: before it can turn away real traffic.
shadow_mode = env("FIREWALL_SHADOW_MODE", False)

#: Paths that skip the firewall entirely (comma-separated), so an automated
#: health check hitting the same path thousands of times a day never trips
#: threat detection or accumulates a reputation score it did nothing to earn.
health_exempt_paths = env("FIREWALL_HEALTH_EXEMPT_PATHS", "/health,/healthz,/ping")

#: Reputation points that decay per day of inactivity - an IP that triggered
#: one signature two months ago and has been clean since should not still be
#: sitting at the same score as the day it happened. 0 disables decay.
reputation_decay_per_day = env("FIREWALL_REPUTATION_DECAY_PER_DAY", 5)
