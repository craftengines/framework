"""Authentication configuration."""

from codepy.config import env

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
