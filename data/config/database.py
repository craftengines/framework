"""Database configuration."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.config import env

# SQLite needs no server or credentials, so a fresh checkout runs out of the
# box; Docker and production set DB_CONNECTION explicitly.
default = env("DB_CONNECTION", "sqlite")

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
        # Connect as a role that owns nothing, is not a superuser, and has no
        # BYPASSRLS. Row-level security does not apply to any of those, so
        # tenant isolation policies would be inert and nothing about the tables
        # would say so — `dev.py db:audit-rls` reports it, and the ScopeTenant
        # middleware refuses to serve tenant traffic under such a role.
        # Migrations run as the owning role, which is a separate credential.
        "username": env("DB_USERNAME", "forge"),
        "password": env("DB_PASSWORD", ""),
        "sslmode": env("DB_SSLMODE", "prefer"),
        # How many physical connections this process may hold. A thread that
        # needs one while all are checked out waits `pool_timeout` seconds and
        # then raises, rather than blocking forever.
        "pool_size": env("DB_POOL_SIZE", 10),
        "pool_timeout": env("DB_POOL_TIMEOUT", 30),
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
