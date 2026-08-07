"""Authentication configuration."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.config import env

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

password_timeout = 10800
