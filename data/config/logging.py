"""Logging configuration."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import os

channels = {
    "single": {
        "driver": "single",
        "path": "storage/logs/craft.log",
        "level": "debug",
    },
    "daily": {
        "driver": "daily",
        "path": "storage/logs/craft.log",
        "level": "debug",
        "days": 7,
    },
    "stderr": {
        "driver": "stderr",
        "level": "debug",
    },
}

default = "single"
