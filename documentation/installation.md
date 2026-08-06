# Installation

## Requirements

- **Python 3.11 or newer.** The suite is validated on 3.11 and 3.14.
- A database: SQLite (bundled), PostgreSQL, or MySQL.

## Setup

```bash
git clone <repository-url> my-app
cd my-app
pip install -e ".[dev]"
```

`[dev]` adds `pytest` and `httpx`. For a production install, drop it.

Optional extras:

```bash
pip install -e ".[mysql]"   # PyMySQL
pip install -e ".[redis]"   # Redis cache store
```

## Configure

```bash
cp .env.example .env
python craft.py key:generate
```

`key:generate` writes `APP_KEY`, which signs session cookies. Skip it and the
framework falls back to a random per-process key — sessions work, but they do
not survive a restart and are not shared between workers.

Point `.env` at your database:

```ini
DB_CONNECTION=pgsql          # sqlite | pgsql | mysql
DB_HOST=127.0.0.1
DB_PORT=5432
DB_DATABASE=my_app
DB_USERNAME=postgres
DB_PASSWORD=secret
```

For SQLite, only two lines matter:

```ini
DB_CONNECTION=sqlite
DB_DATABASE=storage/database.sqlite
```

## Create the schema

```bash
python craft.py migrate --seed
```

Confirm the connection first if you like:

```bash
python craft.py db ping
python craft.py db show
```

## Run

```bash
python craft.py serve
```

The application is at `http://127.0.0.1:8000`. Use `--host`, `--port` and
`--no-reload` to change how it runs.

## Docker

`docker-compose.yml` brings up the app and PostgreSQL together:

```bash
docker compose up -d --build
```

- Application: `http://localhost:8300`
- PostgreSQL: `localhost:5499` (user `codepy`, database `codepy_db`)

Run the suite inside the container to check the minimum Python version:

```bash
docker exec framework python -m pytest
```

The database uses a named volume, so recreating the container keeps your data.

## Verify

```bash
python -m pytest
```

## Directory layout

```
app/                     Your application code
  Http/Controllers/      Controllers
  Http/Middleware/       Middleware
  Http/Requests/         FormRequests
  Http/Resources/        JSON transformers
  Models/                Codepyquent models
  Policies/ Events/ Listeners/ Jobs/ Providers/ Services/
bootstrap/app.py         Builds the container, registers providers, mounts the kernel
config/                  app, auth, cache, database, logging, queue, session
database/                migrations/ seeders/ factories/
public/index.py          Front controller (`application = asgi_app`)
resources/views/         Forge templates
resources/lang/          Translation catalog
routes/                  web.py, api.py, console.py
services/                The framework itself, imported as codepy.*
storage/                 Logs, cache, sessions
tests/                   Test suite
craft.py                 CLI entry point
```

## Troubleshooting

**`ModuleNotFoundError: No module named 'services'`** — run commands from the
project root, or install with `pip install -e .`.

**`psycopg2` errors on connect** — check `db ping` output and confirm the
database exists. `craft` cannot create the database itself.

**Passwords hash slowly, or a bcrypt warning appears** — `passlib` breaks with
bcrypt 4.1+. The dependency is pinned to `<4.1`; if your environment has a newer
one, the framework falls back to PBKDF2 rather than failing.
