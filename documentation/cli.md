# The craft CLI

```bash
python craft.py <command>
```

Laravel-style colons work, and so does the plain form: `migrate:status` and
`migrate status` are the same command.

## Migrations

| Command | What it does |
|---|---|
| `migrate` | Apply pending migrations |
| `migrate --step N` | Apply only the first N pending |
| `migrate --pretend` | Print what would run, touching nothing |
| `migrate --seed` | Migrate, then run the DatabaseSeeder |
| `migrate:status` | Which migrations ran, and in which batch |
| `migrate:rollback` | Revert the last batch |
| `migrate:rollback --step N` | Revert the last N batches |
| `migrate:reset` | Revert everything |
| `migrate:refresh` | Reset, then re-run |
| `migrate:fresh` | Drop every table, then re-run |
| `migrate:install` | Create the migrations table only |

`refresh` and `fresh` both accept `--seed`.

## Database

| Command | What it does |
|---|---|
| `db seed` | Run `DatabaseSeeder` |
| `db seed --class UserSeeder` | Run one seeder |
| `db show` | Connection, driver, host, database |
| `db tables` | List tables |
| `db ping` | Verify the connection; non-zero exit on failure |
| `db wipe --force` | Drop every table |

`db wipe` refuses to run without `--force`.

## Generators

| Command | Creates |
|---|---|
| `make model Product` | `app/Models/Product.py` |
| `make model Product -m` | Model plus a create migration |
| `make controller Product` | `app/Http/Controllers/ProductController.py` |
| `make controller Product -r` | Controller with index/show/store/update/destroy |
| `make migration create_products_table` | Timestamped migration |
| `make migration add_color_to_products_table` | An alter migration |
| `make middleware EnsureAdmin` | `app/Http/Middleware/` |
| `make request StoreProduct` | FormRequest |
| `make resource Product` | API resource |
| `make job SendEmail` | Queued job |
| `make event OrderPlaced` | Event |
| `make listener NotifyTeam` | Listener |
| `make policy Product` | Policy |
| `make seeder Product` | Seeder |
| `make factory Product` | Factory |
| `make service Billing` | Plain service class |

Names are normalised: `service_order`, `service-order` and `ServiceOrder` all
produce `ServiceOrder`. Suffixes are added once — `make controller Product` and
`make controller ProductController` both give `ProductController`.

Generators refuse to overwrite. Pass `--force` when you mean it.

Migration names drive the stub: `create_*_table` produces a create migration and
`add_*_to_*_table` produces an alter migration, with the table inferred.

## Routes

```bash
python craft.py route list
python craft.py route list --method POST
python craft.py route list --path /api
```

## Queue

```bash
python craft.py queue work
python craft.py queue work --queue emails
python craft.py queue work --once
```

See [Queues and events](queues_events.md).

## Cache

```bash
python craft.py cache clear
```

## Application

| Command | What it does |
|---|---|
| `serve` | Development server (`--host`, `--port`, `--no-reload`) |
| `tinker` | Interactive shell with the app booted |
| `about` | Environment, debug, Python, database, cache, queue |
| `key:generate` | Generate `APP_KEY` and write it to `.env` |

`tinker` gives you `app`, `db` and the facades:

```python
>>> from app.Models.User import User
>>> User.query().count()
3
```

## Exit codes

Commands exit non-zero on failure, so they compose in scripts and CI:

```bash
python craft.py db ping && python craft.py migrate
```

## Adding a command

`craft` is built with [Typer](https://typer.tiangolo.com/). Add commands in
`services/cli/app.py`:

```python
@cli.command("stats")
def stats():
    """Show application statistics."""
    app = get_app()
    total = app.make("db").statement("SELECT COUNT(*) AS n FROM users").fetchone()
    echo(f"Users: {total['n']}")
```

Use `get_app()` to boot the application lazily — importing it at module level
would slow down every command, including `--help`.
