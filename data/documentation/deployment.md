# Deployment

## Checklist

Work through this before the first production request.

- [ ] `python dev.py key:generate` — with `APP_ENV=production` and no
      `APP_KEY`, the app now refuses to boot rather than degrading silently.
      Outside production, an empty `APP_KEY` falls back to a random
      per-process key: sessions break on restart and are not shared between
      workers.
- [ ] `APP_DEBUG=false` — with it on, stack traces reach the client.
- [ ] `APP_ENV=production`
- [ ] `SESSION_SECURE_COOKIE=true` — the cookie becomes HTTPS-only.
- [ ] Serve `public/` as the web root. `storage/`, `.env`, `app/` and `config/`
      must not be reachable over HTTP.
- [ ] `python dev.py migrate` — never `migrate:fresh`, which drops everything.
- [ ] Confirm `python dev.py db ping` succeeds as the deploy user.
- [ ] Set up a queue worker if you dispatch jobs.

## The ASGI entry point

`public/index.py` exposes `application`:

```python
from bootstrap.app import asgi_app

application = asgi_app
```

Run it with any ASGI server:

```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker public.index:application \
  --bind 0.0.0.0:8000
```

```bash
uvicorn public.index:application --host 0.0.0.0 --port 8000 --workers 4
```

`dev serve` is for development. It enables reload and binds to localhost.

## Docker

`Dockerfile.prod` is a multi-stage build that installs runtime dependencies
only, drops privileges to a non-root `dev` user, and serves through Gunicorn.

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Set through the environment, not a committed `.env`:

```yaml
environment:
  - APP_ENV=production
  - APP_DEBUG=false
  - APP_KEY=${APP_KEY}
  - DB_CONNECTION=pgsql
  - DB_HOST=db
  - DB_DATABASE=${DB_DATABASE}
  - DB_USERNAME=${DB_USERNAME}
  - DB_PASSWORD=${DB_PASSWORD}
  - SESSION_SECURE_COOKIE=true
```

## Multiple workers

Some defaults do not survive more than one process:

| Default | Problem | Fix |
|---|---|---|
| `SESSION_DRIVER=cookie` | Fine — the payload travels with the client | — |
| `CACHE_DRIVER=array` | Each worker caches separately | `file` on one host, `redis` across hosts |
| Missing `APP_KEY` | Each worker signs with a different key, so sessions break as requests move between workers | `key:generate` |

With `SESSION_DRIVER=file`, every worker needs the same
`storage/framework/sessions` — a shared volume, or use `cookie`.

## Queue workers

```bash
python dev.py queue work --queue default
```

Run it under a supervisor that restarts it — systemd, supervisord, or a separate
container. The `sync` driver runs jobs inline and needs no worker, but it makes
the request wait.

## Migrations on deploy

```bash
python dev.py migrate
```

It is idempotent: already-applied migrations are skipped. Check first with
`migrate:status`, and rehearse a rollback:

```bash
python dev.py migrate:status
python dev.py migrate:rollback --step 1
```

## Multi-tenancy

PostgreSQL schema-per-tenant is supported:

```python
DB.set_tenant_schema("tenant_42")     # switch search_path
DB.ensure_tenant_schema("tenant_42")  # create and migrate if new
```

On drivers without schema support this is a no-op, so tenant-aware middleware
still runs in development against SQLite.

## Logging

Errors go through the exception handler. Server faults (5xx) are logged with a
stack trace; client errors (4xx) are logged at info level without one, so a wave
of 404s or failed CSRF checks does not bury a real fault.

Configure the handler in `config/logging.py`. In containers, log to stdout and
let the platform collect it.

## Health check

```python
Route.get("/health", lambda: {"status": "ok"}).name("health")
```

For a check that proves the database too:

```python
def health(request):
    app.make("db").statement("SELECT 1")
    return {"status": "ok"}
```

## What to back up

- The database.
- `.env` — specifically `APP_KEY`. Lose it and every existing session is
  invalidated.
- `storage/app/` if you store uploads there.

`storage/framework/cache` and `storage/framework/sessions` are disposable.
