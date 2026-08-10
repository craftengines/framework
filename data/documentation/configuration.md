# Configuration

Configuration lives in `config/` as plain Python modules. Every value is
readable through dot notation, and secrets come from the environment.

## The `.env` file

`Application.register_config()` loads `.env` before any config module runs, so
`env()` sees your values. Real environment variables always win over the file —
in production you can set them directly and ship no `.env` at all.

```ini
APP_NAME=Craft
APP_ENV=local
APP_DEBUG=true
APP_KEY=base64:...

DB_CONNECTION=pgsql
DB_HOST=127.0.0.1

MAIL_FROM_NAME="${APP_NAME}"
```

`${VAR}` interpolates values already loaded. `null`, `none` and empty strings
resolve to the default you pass to `env()`.

`.env` is gitignored. `.env.example` is committed and documents every key.

## Config modules

Each file in `config/` becomes a namespace:

```python
# config/app.py
from craft.config import env

APP_NAME = env("APP_NAME", "Craft")
# Debug is opt-in: it defaults to False so a missing .env never leaks stack
# traces in production. Set APP_DEBUG=true locally.
APP_DEBUG = env("APP_DEBUG", False)
APP_LOCALE = env("APP_LOCALE", "en")
APP_FALLBACK_LOCALE = env("APP_FALLBACK_LOCALE", "en")
```

Read them by file name and key:

```python
from craft.facades import Config

Config.get("app.APP_NAME")
Config.get("database.connections.pgsql.host")
Config.get("nothing.here", "fallback")
```

Keys are registered in both their original and lowercased form, so
`Config.get("app.app_name")` also works.

Set values at runtime — useful in tests:

```python
Config.set("cache.default", "array")
```

> Configuration is shared for the process. A test that changes a value must put
> it back, or every later test sees the change.

## `env()` type coercion

| In `.env` | Python value |
|---|---|
| `true` / `false` | `True` / `False` |
| `8000` | `8000` (int) |
| `null` / `none` / empty | the default you passed |
| anything else | `str` |

## What ships in `config/`

| File | Purpose |
|---|---|
| `app.py` | Name, environment, debug (off by default), key, locale, timezone |
| `framework.py` | Framework name/version/release, feature flags (`MULTI_TENANCY_ENABLED`, `PQC_SECURITY_ENABLED`, `CAPTCHA_ENABLED`), default locale and supported locales |
| `database.py` | Connections for sqlite, pgsql, mysql |
| `session.py` | Driver, lifetime, cookie name, SameSite, CSRF switch |
| `auth.py` | Guards and the user provider model |
| `cache.py` | Default store |
| `queue.py` | Default connection |
| `logging.py` | Log channel setup |

## Database connections

```python
# config/database.py
# sqlite by default, so a fresh checkout runs with no database service;
# Docker and production set DB_CONNECTION explicitly.
default = env("DB_CONNECTION", "sqlite")

connections = {
    "sqlite": {"driver": "sqlite", "database": env("DB_DATABASE", "storage/database.sqlite")},
    "pgsql": {
        "driver": "postgresql",
        "host": env("DB_HOST", "127.0.0.1"),
        "port": env("DB_PORT", 5432),
        "database": env("DB_DATABASE", "forge"),
        "username": env("DB_USERNAME", "forge"),
        "password": env("DB_PASSWORD", ""),
    },
}
```

Split reads from writes by nesting `read` and `write`:

```python
"pgsql": {
    "driver": "postgresql",
    "host": "127.0.0.1",
    "username": "craft",
    "password": "secret",
    "write": {"host": "primary.db.internal"},
    "read": {"host": "replica.db.internal"},
}
```

Keys outside `read`/`write` apply to both.

### Connection pool

Requests are served on a thread pool, and each thread borrows a connection for
the duration of the request and gives it back afterwards. Two keys size that
pool, per connection:

```python
"pgsql": {
    "driver": "postgresql",
    # ...
    "pool_size": 10,      # physical connections (default 10)
    "pool_timeout": 30,   # seconds to wait for a free one (default 30)
}
```

`pool_size` is a ceiling on connections to that database *per worker process*,
so the total your server opens is `pool_size × workers` — keep that under the
database's own `max_connections`. When every connection is checked out, a
request waits up to `pool_timeout` and then fails with an error naming the
setting, rather than hanging forever.

SQLite `:memory:` is the one exception: an in-memory database lives inside the
connection that created it, so all threads share a single connection there.

## Sessions

```python
# config/session.py
driver = env("SESSION_DRIVER", "cookie")     # cookie | file
lifetime = env("SESSION_LIFETIME", 7200)
cookie = env("SESSION_COOKIE", "craft_session")
secure = env("SESSION_SECURE_COOKIE", False)
same_site = env("SESSION_SAME_SITE", "lax")
csrf = env("SESSION_CSRF", True)
```

See [Sessions](sessions.md) for the difference between the drivers.

## Adding your own

Drop a file in `config/`:

```python
# config/services.py
from craft.config import env

stripe = {
    "key": env("STRIPE_KEY", ""),
    "secret": env("STRIPE_SECRET", ""),
}
```

```python
Config.get("services.stripe.key")
```

## Inspecting configuration

```bash
python dev.py about     # environment, debug, database, cache, queue
python dev.py db show   # the active connection
```
