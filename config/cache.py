"""Cache configuration."""

from codepy.config import env

default = env("CACHE_DRIVER", "memory")

stores = {
    "memory": {
        "driver": "memory",
    },
    "file": {
        "driver": "file",
        "path": "storage/framework/cache",
    },
    "redis": {
        "driver": "redis",
        "host": env("REDIS_HOST", "127.0.0.1"),
        "port": env("REDIS_PORT", 6379),
    },
}
