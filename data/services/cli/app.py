"""The `dev` command line interface for Craft Framework.

Migrations, seeding, generators, routing inspection,
queue workers and the development server.

Category: Core Framework (CLI).
Relations:
  - Invoked by `dev.py`, which pre-splits `group:subcommand` tokens (e.g.
    `migrate:status`) into `group subcommand` before handing off to Typer.
  - Generators live in `services/cli/generators.py`.
References:
  - Guide: `documentation/cli.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import os
import sys
from typing import Any, List, Optional

import typer

cli = typer.Typer(
    name="dev",
    help="Craft Framework console.",
    no_args_is_help=True,
    add_completion=False,
)

make_app = typer.Typer(name="make", help="Generate framework classes.", no_args_is_help=True)
migrate_app = typer.Typer(name="migrate", help="Run database migrations.", invoke_without_command=True)
db_app = typer.Typer(name="db", help="Database utilities.", no_args_is_help=True)
queue_app = typer.Typer(name="queue", help="Queue workers.", no_args_is_help=True)
route_app = typer.Typer(name="route", help="Routing utilities.", no_args_is_help=True)
cache_app = typer.Typer(name="cache", help="Cache utilities.", no_args_is_help=True)
plugin_app = typer.Typer(name="plugin", help="Plugin discovery and lifecycle.", no_args_is_help=True)

cli.add_typer(make_app)
cli.add_typer(migrate_app)
cli.add_typer(db_app)
cli.add_typer(queue_app)
cli.add_typer(route_app)
cli.add_typer(cache_app)
cli.add_typer(plugin_app)


# -- application bootstrap ------------------------------------------------------

_app_instance: Any = None


def base_path() -> str:
    return os.getcwd()


def get_app(boot_http: bool = False) -> Any:
    """Boot (once) and return the Craft application."""
    global _app_instance
    if _app_instance is not None:
        return _app_instance

    if base_path() not in sys.path:
        sys.path.insert(0, base_path())

    import services  # registers the `craft.*` module aliases  # noqa: F401

    if boot_http:
        from bootstrap.app import app as booted
    else:
        from bootstrap.app import create_app

        booted = create_app()

    _app_instance = booted
    return _app_instance


def get_migrator() -> Any:
    from services.migrations.migrator import Migrator

    return Migrator(get_app())


def echo(message: str, color: Optional[str] = None) -> None:
    typer.echo(typer.style(message, fg=color) if color else message)


# -- migrate --------------------------------------------------------------------

@migrate_app.callback()
def migrate(
    ctx: typer.Context,
    step: Optional[int] = typer.Option(None, help="Only run the first N pending migrations."),
    pretend: bool = typer.Option(False, help="Print what would run without touching the database."),
    seed: bool = typer.Option(False, help="Run the DatabaseSeeder afterwards."),
) -> None:
    """Run all pending migrations."""
    if ctx.invoked_subcommand is not None:
        return

    migrator = get_migrator()
    migrator.run(step=step, pretend=pretend)
    for note in migrator.notes:
        echo(note, "green")

    if seed:
        _run_seeder("DatabaseSeeder")


@migrate_app.command("rollback")
def migrate_rollback(step: int = typer.Option(1, help="How many batches to revert.")) -> None:
    """Roll back the last batch of migrations."""
    migrator = get_migrator()
    migrator.rollback(step=step)
    for note in migrator.notes:
        echo(note, "yellow")


@migrate_app.command("reset")
def migrate_reset() -> None:
    """Roll back every migration."""
    migrator = get_migrator()
    migrator.reset()
    for note in migrator.notes:
        echo(note, "yellow")


@migrate_app.command("refresh")
def migrate_refresh(seed: bool = typer.Option(False, help="Seed after refreshing.")) -> None:
    """Roll back and re-run every migration."""
    migrator = get_migrator()
    migrator.refresh()
    for note in migrator.notes:
        echo(note, "green")
    if seed:
        _run_seeder("DatabaseSeeder")


@migrate_app.command("fresh")
def migrate_fresh(seed: bool = typer.Option(False, help="Seed after rebuilding.")) -> None:
    """Drop every table and re-run all migrations."""
    migrator = get_migrator()
    migrator.fresh()
    for note in migrator.notes:
        echo(note, "green")
    if seed:
        _run_seeder("DatabaseSeeder")


@migrate_app.command("status")
def migrate_status() -> None:
    """Show which migrations have run."""
    rows = get_migrator().status()
    if not rows:
        echo("No migrations found.", "yellow")
        return

    echo(f"{'Ran?':<6} {'Batch':<7} Migration")
    echo("-" * 78)
    for row in rows:
        mark = "Yes" if row["ran"] else "No"
        batch = str(row["batch"] or "")
        echo(f"{mark:<6} {batch:<7} {row['migration']}")


@migrate_app.command("install")
def migrate_install() -> None:
    """Create the migration repository table."""
    get_migrator().ensure_repository()
    echo("Migration table created successfully.", "green")


# -- db -------------------------------------------------------------------------

def _run_seeder(name: str) -> None:
    from services.seeding import run_seeder

    app = get_app()
    seeder = run_seeder(name, app)
    for note in getattr(seeder, "command_output", []):
        echo(note, "green")
    echo(f"Database seeding completed ({name}).", "green")


@db_app.command("seed")
def db_seed(
    seeder: str = typer.Option("DatabaseSeeder", "--class", help="Seeder class to run.")
) -> None:
    """Seed the database with records."""
    _run_seeder(seeder)


@db_app.command("show")
def db_show() -> None:
    """Show the active database connection."""
    app = get_app()
    db = app.make("db")
    config = app.make("config")
    name = config.get("database.default")
    settings = config.get(f"database.connections.{name}", {}) or {}

    echo(f"Connection : {name}")
    echo(f"Driver     : {db.driver}")
    echo(f"Host       : {settings.get('host', '-')}")
    echo(f"Port       : {settings.get('port', '-')}")
    echo(f"Database   : {settings.get('database', '-')}")


@db_app.command("ping")
def db_ping() -> None:
    """Verify the database connection is reachable."""
    try:
        db = get_app().make("db")
        db.statement("SELECT 1")
        echo(f"Connection OK ({db.driver}).", "green")
    except Exception as exc:
        echo(f"Connection FAILED: {exc}", "red")
        raise typer.Exit(code=1)


@db_app.command("tables")
def db_tables() -> None:
    """List the tables in the current database."""
    app = get_app()
    db = app.make("db")
    if db.driver == "sqlite":
        sql = "SELECT name AS table_name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    elif db.driver == "postgresql":
        sql = "SELECT tablename AS table_name FROM pg_tables WHERE schemaname = current_schema() ORDER BY tablename"
    else:
        sql = "SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE() ORDER BY table_name"

    for row in db.statement(sql, read=True).fetchall():
        echo(f"  {row['table_name']}")


@db_app.command("wipe")
def db_wipe(
    confirm: bool = typer.Option(False, "--force", help="Required — this drops every table.")
) -> None:
    """Drop every table in the database."""
    if not confirm:
        echo("Refusing to wipe without --force.", "red")
        raise typer.Exit(code=1)
    get_migrator().drop_all_tables()
    echo("Database wiped.", "yellow")


# -- make -----------------------------------------------------------------------

@make_app.command("model")
def make_model(
    name: str,
    migration: bool = typer.Option(False, "-m", "--migration", help="Also create a migration."),
    force: bool = typer.Option(False, "--force"),
) -> None:
    """Create a new Craft ORM model."""
    from services.cli import generators

    path = generators.generate("model", name, base_path(), force=force)
    echo(f"Model created: {path}", "green")

    if migration:
        table = generators.table_for(generators.studly(name))
        migration_path = generators.generate_migration(
            f"create_{table}_table", base_path(), table=table, create=True
        )
        echo(f"Migration created: {migration_path}", "green")


@make_app.command("migration")
def make_migration(
    name: str,
    table: Optional[str] = typer.Option(None, help="Target table."),
    create: bool = typer.Option(True, help="Create a table (vs. alter one)."),
) -> None:
    """Create a new migration file."""
    from services.cli import generators

    path = generators.generate_migration(name, base_path(), table=table, create=create)
    echo(f"Migration created: {path}", "green")


@make_app.command("controller")
def make_controller(
    name: str,
    resource: bool = typer.Option(False, "-r", "--resource", help="Generate CRUD methods."),
    force: bool = typer.Option(False, "--force"),
) -> None:
    """Create a new controller."""
    from services.cli import generators

    path = generators.generate("controller", name, base_path(), force=force, resource=resource)
    echo(f"Controller created: {path}", "green")


@make_app.command("crud")
def make_crud(
    entity: str,
    fields: str = typer.Option(
        "",
        "--fields",
        help='Field list: "name:type:rule1|rule2,other:type". Defaults to string, nullable.',
    ),
    force: bool = typer.Option(False, "--force"),
) -> None:
    """Generate a full CRUD slice: migration, model, controller, request, resource, route."""
    from services.cli import crud_builder

    field_list = crud_builder.parse_fields(fields) if fields else []
    result = crud_builder.build_crud(entity, field_list, base_path(), force=force)

    echo(f"CRUD generated for [{result['entity']}]:", "green")
    for kind, path in result["files"].items():
        echo(f"  {kind:<12} {path}", "green")


def _simple_generator(kind: str, label: str):
    def command(name: str, force: bool = typer.Option(False, "--force")) -> None:
        from services.cli import generators

        path = generators.generate(kind, name, base_path(), force=force)
        echo(f"{label} created: {path}", "green")

    command.__doc__ = f"Create a new {label.lower()}."
    return command


for _kind, _label in [
    ("middleware", "Middleware"),
    ("request", "Form request"),
    ("resource", "Resource"),
    ("job", "Job"),
    ("event", "Event"),
    ("listener", "Listener"),
    ("policy", "Policy"),
    ("seeder", "Seeder"),
    ("factory", "Factory"),
    ("service", "Service"),
]:
    make_app.command(_kind)(_simple_generator(_kind, _label))


# -- routes ---------------------------------------------------------------------

@route_app.command("list")
def route_list(
    method: Optional[str] = typer.Option(None, help="Filter by HTTP method."),
    path_filter: Optional[str] = typer.Option(None, "--path", help="Filter by URI substring."),
) -> None:
    """List every registered route."""
    app = get_app(boot_http=True)
    router = app.make("router")

    echo(f"{'METHOD':<16} {'URI':<44} NAME")
    echo("-" * 96)
    count = 0
    for route in router.routes:
        methods = "|".join(m for m in route.methods if m != "HEAD")
        if method and method.upper() not in route.methods:
            continue
        if path_filter and path_filter not in route.uri:
            continue
        echo(f"{methods:<16} {route.uri:<44} {route._name or '-'}")
        count += 1
    echo("-" * 96)
    echo(f"{count} route(s).")


# -- queue ----------------------------------------------------------------------

@queue_app.command("work")
def queue_work(
    queue: str = typer.Option("default", help="Queue name to process."),
    once: bool = typer.Option(False, help="Process a single job then exit."),
) -> None:
    """Process jobs from the queue."""
    import time

    manager = get_app().make("queue")
    echo(f"Processing jobs from the [{queue}] queue.", "green")
    while True:
        processed = manager.work(queue)
        if processed:
            echo("Processed a job.", "green")
        if once:
            break
        if not processed:
            time.sleep(1)


# -- cache ----------------------------------------------------------------------

@cache_app.command("clear")
def cache_clear() -> None:
    """Flush the application cache."""
    get_app().make("cache").flush()
    echo("Application cache cleared.", "green")


# -- plugin ---------------------------------------------------------------------

@plugin_app.command("list")
def plugin_list() -> None:
    """List every plugin known to the application (DB or in-memory)."""
    manager = get_app().make("plugin")

    echo(f"{'SLUG':<24} {'NAME':<28} {'ENABLED':<9} PATH")
    echo("-" * 96)
    for entry in manager.installed():
        enabled = "Yes" if entry.get("enabled") else "No"
        echo(f"{entry.get('slug', '-'):<24} {entry.get('name', '-'):<28} {enabled:<9} {entry.get('path') or '-'}")


@plugin_app.command("enable")
def plugin_enable(slug: str) -> None:
    """Enable a plugin by slug."""
    manager = get_app().make("plugin")
    if not manager.enable(slug):
        echo(f"No such plugin: {slug}", "red")
        raise typer.Exit(code=1)
    echo(f"Plugin enabled: {slug}", "green")


@plugin_app.command("disable")
def plugin_disable(slug: str) -> None:
    """Disable a plugin by slug."""
    manager = get_app().make("plugin")
    if not manager.disable(slug):
        echo(f"No such plugin: {slug}", "red")
        raise typer.Exit(code=1)
    echo(f"Plugin disabled: {slug}", "green")


@plugin_app.command("sync")
def plugin_sync() -> None:
    """Discover plugins on disk and register newly found ones in the database."""
    manager = get_app().make("plugin")
    newly_registered = manager.sync(base_path())
    if newly_registered:
        echo(f"Registered {len(newly_registered)} new plugin(s): {', '.join(newly_registered)}", "green")
    else:
        echo("No new plugins found.", "yellow")


# -- top-level commands ---------------------------------------------------------

@cli.command("serve")
def serve(
    host: str = typer.Option("127.0.0.1", help="Bind host."),
    port: int = typer.Option(8000, help="Bind port."),
    reload: bool = typer.Option(True, help="Reload on file changes."),
) -> None:
    """Start the development server."""
    import uvicorn

    echo(f"Craft development server started on http://{host}:{port}", "green")
    uvicorn.run("bootstrap.app:asgi_app", host=host, port=port, reload=reload)


@cli.command("tinker")
def tinker() -> None:
    """Open an interactive shell with the application booted."""
    import code

    app = get_app()
    context = {"app": app, "db": app.make("db")}
    try:
        from craft.facades import Config, DB, Route  # type: ignore

        context.update({"Config": Config, "DB": DB, "Route": Route})
    except Exception:
        pass
    code.interact(banner="Craft tinker — `app`, `db` and facades are available.", local=context)


@cli.command("about")
def about() -> None:
    """Show framework and environment information."""
    import platform

    app = get_app()
    config = app.make("config")
    echo("Craft Framework")
    echo(f"  Environment  : {config.get('app.env', 'local')}")
    echo(f"  Debug        : {config.get('app.debug', False)}")
    echo(f"  Python       : {platform.python_version()}")
    echo(f"  Database     : {app.make('db').driver}")
    echo(f"  Cache        : {config.get('cache.default', 'array')}")
    echo(f"  Queue        : {config.get('queue.default', 'sync')}")


@cli.command("key:generate")
def key_generate() -> None:
    """Generate an application key and write it to `.env`."""
    import secrets

    key = "base64:" + secrets.token_urlsafe(32)
    env_path = os.path.join(base_path(), ".env")

    lines: List[str] = []
    if os.path.isfile(env_path):
        with open(env_path, "r", encoding="utf-8") as handle:
            lines = handle.read().splitlines()

    replaced = False
    for index, line in enumerate(lines):
        if line.startswith("APP_KEY="):
            lines[index] = f"APP_KEY={key}"
            replaced = True
            break
    if not replaced:
        lines.append(f"APP_KEY={key}")

    with open(env_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")

    echo(f"Application key set: {key}", "green")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
