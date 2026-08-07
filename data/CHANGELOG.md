# Changelog

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: `MAJOR.MINOR.PATCH` plus a release counter (`rNNNNN`) that
increments on every cut release, tracked in `services/__init__.py`
(`__version__`, `__release__`) and `pyproject.toml`.

**Every change to `services/`, `app/`, `bootstrap/`, `config/`, `database/`,
`routes/`, or `dev.py` gets an entry here, in the same change/PR that makes
it** — not batched later, not left for the release cut to reconstruct from
memory or `git log`. This applies to humans and AI agents alike: a bug fixed,
a feature added, a dependency bumped, a vulnerability closed. If it isn't
here, an agent reading this file has no way to know it happened without
re-deriving it from the diff — which is exactly the blind spot this file
exists to remove. See "Versioning and releases" in `CONTRIBUTING.md` for the
full policy (categories to use, what counts as security-relevant, how
`[Unreleased]` gets folded into a release).

---

## [Unreleased]

### Fixed

- `.agents/skills/framework/craft-development/SKILL.md` still claimed the ORM
  "wraps SQLAlchemy 2.0 Core" — missed by the earlier documentation audit
  because it lives outside `data/`. It's a custom query builder over
  `sqlite3`/`psycopg2`/`PyMySQL`; no SQLAlchemy, no Pydantic.

### Changed

- Every change to the framework now requires a `CHANGELOG.md` entry in the
  same commit that makes it (not batched for the release cut) — policy
  documented in `CONTRIBUTING.md` ("Every change gets a CHANGELOG entry") and
  in `.agents/skills/framework/craft-development/SKILL.md` §3, so both human
  contributors and AI agents working in this repo pick it up.

---

## [3.11.0] r00001 — 2026-08-07

First cut release. Everything below this line — the full validation pass
(15 → 627 tests), the security/reliability hardening, the workspace
reorganization into `data/`, plugin management, and the CRUD builder — ships
as `v3.11.0-r00001`.

### 2026-08-07 — Workspace reorganization, plugin management, CRUD builder

The application skeleton moved to `data/` at the workspace root — that
directory is now the single deployable unit and the Docker Compose project
root (`build: .` / `volumes: .:/app` both resolve relative to `data/`), so
editing any file there is live in the running container immediately. Nothing
outside `data/` is copied into the container image.

### Added

- **CRUD builder** — `dev.py make crud <Entity> --fields "name:type[:rule1|
  rule2],..."` generates a migration, model, `FormRequest`, API `Resource`,
  and a controller wired to real ORM calls (not a placeholder scaffold).
  Registers as a JSON API resource in `routes/api.py` via `Route.api_resource`
  (matching the existing `PostController` convention), not in `routes/web.py`,
  which is behind CSRF verification a JSON client can't satisfy. An admin UI
  at `/admin/crud-builder` (behind `auth`, like `/admin`) drives the same
  `services/cli/crud_builder.py:build_crud()`. Generated write routes have no
  authorization by default — see `documentation/crud-builder.md`.
- **Plugin management**, levelled up to match `ModuleManager`: a `plugins`
  table (migration + `app/Models/Plugin.py`), disk discovery from
  `plugins/<slug>/plugin.py`, DB-backed `installed()/is_enabled()/enable()/
  disable()` with the same try-DB/fallback-to-memory behaviour as
  `ModuleManager` (never fakes success), and `sync()` upserts newly
  discovered plugins without re-enabling one an operator disabled. CLI:
  `dev.py plugin:list/enable/disable/sync`.
- Workspace-level `README.md` and skill `.agents/skills/project/
  workspace-architecture/SKILL.md` documenting the `data/`-as-deployable-unit
  contract and the clone-to-new-app procedure, for both humans and AI agents
  bootstrapping a new project from this repository.
- `Category`/`Relations`/`References` orientation header added to 41 core
  files under `services/`, so an AI agent skimming a file understands its
  role before editing it.

### Fixed

- `dev.py`'s `group:subcommand` convenience (`migrate:status` ==
  `migrate status`) used to split **any** colon-containing argument, which
  silently mangled option values like `--fields "name:string:required"`.
  Now only the leading command token is eligible for the split.
- `documentation/orm.md` claimed the ORM wraps SQLAlchemy 2.0 Core — it
  doesn't; it's a custom query builder over `sqlite3`/`psycopg2`/`PyMySQL`.
- `documentation/security.md` still framed session-cookie signing in terms
  that read as PQC-adjacent; clarified as HMAC-SHA256, with `PQC`
  (`services/security/pqc.py`) called out as the separate, opt-in utility it
  actually is.
- `CRAFT_DESIGN.md` (the original design doc) now carries a banner marking
  it as the aspirational target architecture (FastAPI/asyncpg/SQLAlchemy/
  Pydantic) rather than the current implementation, after it kept misleading
  agents that skimmed it for how the framework actually works.
- Residual Portuguese in English-facing files (`README.md`, this file,
  `SECURITY.md`, and five docstrings) translated.
- `services/validation/validator.py` carried a "Laravel semantics" comment —
  removed (naming-restriction violation: this project names no third-party
  framework anywhere).

### Changed

- Suite: 596 → **627 tests** (plugin persistence + discovery, CRUD builder
  file-shape/idempotency/rule-reflection).

---

### 2026-08-07 — Security hardening and fixes

Hardening and bug-fix pass over the validated skeleton. The suite went from
530 to **596 tests**.

### Security

- `WOTS` (`services/security/pqc.py`) rewritten as a Lamport one-time
  signature over SHA-256 — the previous `verify` did not verify anything.
- The exception page now escapes HTML in everything it prints (message,
  stack, context).
- The CSRF token is no longer accepted via query string — only the parsed
  body (`_token`) or the header, so a cross-site link cannot plant the token.
- On the `file` driver, `regenerate()`/`invalidate()` remove the old
  session file from disk.
- Mass-assignment protection: `Model.create()` respects `fillable`;
  `force_create()` is the explicit bypass for trusted internal input.
- The query builder validates identifiers (tables/columns) and uses an
  operator whitelist.
- `APP_DEBUG` now defaults to off (`config/app.py`); the development `.env`
  is what turns it on.
- `X-Forwarded-For` is only honoured when `app.trusted_proxies` is configured.

### Reliability

- The `database` queue driver reserves jobs atomically: `reserved_at` with a
  90s `retry_after`, and `attempts` counted on claim — two workers never
  grab the same job.
- Events accept listeners named by string.
- Cache: `increment` preserves the TTL and `remember()` caches `None`.
- Settings are stored with a JSON type instead of a raw string.
- Validator: an unknown rule now raises instead of silently passing;
  `min`/`max`/`between` measure the numeric value of `integer`/`numeric`
  strings; custom messages accept the `field.rule` form.

### ORM

- `where(column, op, None)` becomes `IS NULL`; `or_where` preserves the
  soft-delete scope.
- `find()` honours a custom `primary_key`.
- Reads inside a transaction use the write connection.
- SQLite opens transactions with `BEGIN IMMEDIATE`; on PostgreSQL, metadata
  queries respect the active schema.
- The migrator ignores files that are not migrations and does not choke on
  a rollback whose file has disappeared.

### Fixes

- `ModuleManager`/`Settings` access rows by column name (dict cursors on
  MySQL/PostgreSQL).
- `PostController`: `edit`/`update` return 404 for a non-existent post.
- Forge directives handle nested parentheses.
- `url_for` URL-encodes values and raises for a missing parameter.
- Async controller actions are awaited (`await`).

### DX

- SQLite is the default database (`config/database.py` + `.env.example`):
  the quickstart runs with no database server — `cp .env.example .env`,
  `key:generate`, `migrate --seed`, `serve`.

---

### Validation pass — from "does not matter" to a green suite

Validation work on the base skeleton, from "does not matter" to 530 green
tests on SQLite, real PostgreSQL, and Python 3.11.

### Added

**Database**

- Multi-driver connection layer (`services/orm/connection.py`): SQLite,
  PostgreSQL and MySQL with the same SQL. `?` and `:name` placeholders are
  translated to each driver's paramstyle.
- Read/write splitting and schema-per-tenant on PostgreSQL
  (`set_tenant_schema`, `ensure_tenant_schema`).
- Migrator with batches, `run/rollback/reset/refresh/fresh/status`, `--step`
  and `--pretend`.
- Schema builder with a fluent `Blueprint` and per-dialect DDL, foreign keys
  and composite indexes. Fluent and keyword styles are interchangeable:
  `t.string("cpf").nullable()` == `t.string("cpf", nullable=True)`.

**`dev` CLI**

- `migrate:*`, `db seed/show/tables/ping/wipe`, `route list`, `queue work`,
  `serve`, `tinker`, `key:generate`, and 12 `make:*` generators.
- Accepts both `migrate:status` and `migrate status`.

**HTTP**

- Session with `cookie` and `file` drivers, both signed with HMAC-SHA256
  using `APP_KEY`. Flash data and a CSRF token included.
- `StartSession`, `VerifyCsrfToken`, `Authenticate`, `RequireAuth`, and
  `AuthenticateApiToken` middleware.
- Per-route middleware resolved by alias (`auth`, `api`, `session`, `csrf`).
- `Request` with the body parsed before the pipeline: `input()`, `only()`,
  `boolean()`, `file()`, `session()`, `user()`, `bearer_token()`.
- Forge view engine with its own directives (`@csrf`, `@auth`, `@guest`,
  `@can`, `@if`, `@foreach`, `@extends`, `@section`, `@yield`, `@include`,
  `@method`) and global helpers (`csrf_field`, `auth`, `config`, `route`,
  `session`, `__`).

**ORM**

- Eager loading via `with_()`: one query per relation instead of N+1.
- `HasOne`, `HasMany`, `BelongsTo` and `BelongsToMany` with
  `attach/detach/sync`.
- Soft deletes with `with_trashed()` / `only_trashed()` / `restore()`.
- Query builder with `or_where`, `where_in`, `where_null`, `where_between`,
  `join`, `group_by`, `having`, `paginate`, and aggregates.

**Authentication and validation**

- `Hash` with bcrypt and a PBKDF2-SHA256 fallback.
- `AuthManager` with a persistent session; login rotates the session id.
- Validator grew from 3 to ~30 rules, including `unique` and `exists`.

**i18n**

- BCP 47 locales with a `pt-BR → pt → en` fallback chain.
- `normalize_locale` canonicalizes `PT-br` → `pt-BR` and `EN` → `en`.
- Four seeded locales: `en`, `pt` (European), `pt-BR`, `es`.
- Placeholders: `__("welcome_{name}", "pt-BR", name="Ana")`.
- `resources/lang/catalog.json` with 75 semantic keys × 4 locales, including
  consent copy aligned to LGPD/GDPR (opt-in, essential cookies exempt from
  consent, explicit revocation).

**Other**

- Cache with array/file/redis stores, TTL, `remember` and `increment`.
- Queue with JSON serialization, retry with backoff, and `available_at`.
- Seeders and factories.
- `.env` loading with `${VAR}` interpolation.
- 530-test suite (up from 15).

### Fixed

**Blockers**

- The package did not import: the core lived in `framework/` while the 83
  internal imports said `services.*`.
- `import craft` resolved to an unrelated third-party CUDA package in
  site-packages. Replaced with a `MetaPathFinder` that maps
  `craft.* → services.*`.
- `.env` was never read — `env()` only saw real OS environment variables.

**Security**

- `Gate.allows()` returned `True` for any unknown permission — fail-open.
  It now denies by default.
- Per-route middleware was ignored by the kernel: `.middleware("auth")` was
  decorative.
- The seeder wrote a password in plain text.
- `Starlette(debug=True)` was hardcoded in the kernel, which would leak
  stack traces in production.
- `Resource` leaked the entire model: the base class read
  `self.resource.to_dict()`, so a subclass defining `to_dict()` — which the
  generator emitted — was ignored and unexposed fields shipped in the
  response.

**Behaviour**

- `Model.create` used `SELECT last_insert_rowid()`, which breaks on
  PostgreSQL.
- Incorrect JOIN in `Model.permissions()` (`pr.role_id` instead of
  `pr.permission_id`).
- `FormRequest.validated()` returned the raw body without validating
  anything, ignoring `rules()` and `authorize()`.
- The view engine never rendered a layout: `@extends("layouts.app")`
  delivered raw dot notation to Jinja, and the error was swallowed by a
  `<div>Rendered view: x</div>` placeholder returning HTTP 200.
- `EventDispatcher.listen(Event, SomeListener)` required a list and raised
  `TypeError`; base-class listeners did not hear subclasses.
- `ModuleManager.enable()/disable()` returned `True` even for a
  non-existent module.
- `PluginManager.trigger_hook()` swallowed a plugin's exception without
  logging anything.
- `FacadeMeta.__getattr__` fabricated any attribute, including dunders,
  resolving the container before boot.
- `Container.__init__` unconditionally claimed the global singleton: a
  second `Application` hijacked the process.
- Middleware was instantiated on every request, recreating the session
  store and its signing key — no cookie ever survived.
- `captcha.py` used `Any` without importing it: it passed on Python 3.14
  (lazy annotations, PEP 649) and broke on 3.11, the declared minimum.
- Migration `framework_dynamic_tables`: `role_user` used `uuid` for
  `user_id`, and `permission_role` was dropped in `down()` but never
  created in `up()`.
- Migration `jobs`: `available_at`/`created_at` as INTEGER receiving an ISO
  string.
- 4xx responses were logged with a full traceback, burying real failures.
- `datetime.utcnow()` deprecated on Python 3.12+.

**Documentation**

- `security.md` claimed session cookies were signed with post-quantum
  encryption and "cannot be read." Both false: the signature is
  HMAC-SHA256 and, on the cookie driver, the payload is readable by the
  client (signed, not encrypted).
- The Captcha API was documented with the wrong signature.

### Changed

- The `pt` locale was Brazilian Portuguese mislabelled as generic
  ("Painel de Controle", "Baixar", "Registrar"). Now `pt` is European
  Portuguese and `pt-BR` is Brazilian, with distinct copy.
- `QueueManager` was fake: it built a payload with hardcoded `"TestJob"`
  and `"999"` keys just to make the test pass. Rewritten with real
  serialization.
- `Captcha.validate` had a hardcoded `and code != "WRONG"`. It now uses
  `secrets.compare_digest` and always clears the code (single-use).
- Containers renamed to `framework` and `framework-db`; the Compose
  project pinned to `name: framework`. The dev database got a named
  volume — it used to live in the container layer and vanish on every
  recreation.
- Trimmed dependencies: `sqlalchemy`, `alembic`, `pydantic`,
  `pydantic-settings` and `click` removed, none of them used. `pytest` and
  `httpx` became the `[dev]` extra.
- `bcrypt` pinned to `<4.1`: above that, passlib breaks (`__about__` was
  removed).
- `pyproject.toml`: the entrypoint is now `craft = services.cli.app:main`.
- The repository is now version-controlled (`git init`).

### Removed

- The SoftPax domain (funeral home/cemetery) from the base skeleton: 16
  migrations, 18 models, 26 controllers and 3 view folders.
- Dead files: `app/main.py` (a parallel FastAPI app), `home_controller.py`,
  `BaseModel.py` (SQLAlchemy models), `services/coreengine/`, and 4 empty
  files with no references.
- The `craft-showcase` (vite) landing page from the root.
- `.agents/.agents/` and `.ai/.agents/`, recursively nested directories.
  The `changelog.md` that lived in the nesting was lost in this cleanup;
  this file restarts from the Git history.

**Open source project**

- **MIT** license (`LICENSE`), © 2026 Antonio Santos.
- Authorship metadata, classifiers and URLs in `pyproject.toml`;
  `__author__`, `__email__`, `__license__` and `__copyright__` in the
  package.
- License header in 134 source files.
- `CONTRIBUTING.md` and `SECURITY.md`, with a production checklist and
  known gaps stated rather than hidden.
- Full documentation in `documentation/`: 17 guides with an index, covering
  installation, configuration, the container, routing, controllers, views,
  validation, migrations, the ORM, security, sessions, cache, queues,
  resources, i18n, testing, and deployment, plus the `dev` reference. The
  130 APIs cited were verified against the code.

### Compatibility notes

- **Python 3.11+**. The suite runs on 3.14 locally and 3.11 in the
  container.
- Soft-delete mixins must come **before** `Model` in the class declaration
  (`class Note(SoftDeletes, Model)`), or the MRO makes `Model` win.
- Applications that relied on `pt` carrying Brazilian text should now ask
  for `pt-BR`. The `pt-BR → pt → en` fallback covers missing keys.
