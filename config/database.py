"""Database configuration."""

from codepy.config import env

default = env("DB_CONNECTION", "pgsql")

connections = {
    "sqlite": {
        "driver": "sqlite",
        "database": env("DB_DATABASE", "storage/database.sqlite"),
    },
    "pgsql": {
        "driver": "postgresql",
        "host": env("DB_HOST", "127.0.0.1"),
        "port": env("DB_PORT", 5432),
        "database": env("DB_DATABASE", "forge"),
        "username": env("DB_USERNAME", "forge"),
        "password": env("DB_PASSWORD", ""),
    },
    "mysql": {
        "driver": "mysql",
        "host": env("DB_HOST", "127.0.0.1"),
        "port": env("DB_PORT", 3306),
        "database": env("DB_DATABASE", "forge"),
        "username": env("DB_USERNAME", "forge"),
        "password": env("DB_PASSWORD", ""),
    },
}
