"""Authentication configuration."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

defaults = {
    "guard": "web",
}

guards = {
    "web": {
        "driver": "session",
        "provider": "users",
    },
    "api": {
        "driver": "token",
        "provider": "users",
        "token_name": "api_token",
    },
}

providers = {
    "users": {
        "model": "app.Models.User.User",
    },
}

# NOTE: no `password_timeout` here. It described a confirm-password window
# that Craft does not implement, and nothing read it — a knob with no wiring.

