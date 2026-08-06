"""Logging configuration."""

import os

channels = {
    "single": {
        "driver": "single",
        "path": "storage/logs/codepy.log",
        "level": "debug",
    },
    "daily": {
        "driver": "daily",
        "path": "storage/logs/codepy.log",
        "level": "debug",
        "days": 7,
    },
    "stderr": {
        "driver": "stderr",
        "level": "debug",
    },
}

default = "single"
