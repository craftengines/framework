#!/usr/bin/env python
"""`dev` — the Craft Framework console entrypoint.

Usage:
    python dev.py migrate
    python dev.py migrate:status
    python dev.py make model Product -m
    python dev.py db seed
    python dev.py serve --port 8000
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import services  # noqa: F401,E402  installs the `craft.*` import alias

from services.cli.app import cli  # noqa: E402

#: Commands that are a single name containing a colon, not `group:subcommand`.
_ATOMIC_COMMANDS = {"key:generate"}


def main() -> None:
    # Accept `migrate:status` as well as `migrate status`.
    argv = []
    for arg in sys.argv[1:]:
        if ":" in arg and not arg.startswith("-") and arg not in _ATOMIC_COMMANDS:
            argv.extend(arg.split(":", 1))
        else:
            argv.append(arg)
    cli(args=argv, prog_name="dev")


if __name__ == "__main__":
    main()
