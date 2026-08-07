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

### Added

- **Login page shows the 3 demo accounts, gated by `APP_DEBUG`.**
  `resources/views/auth/login.forge.py` now renders a small credentials
  table under the form when `config("app.APP_DEBUG")` is true — never in a
  production build. Discoverable without opening the README.
- `documentation/authorization.md` gained a **Recipes** section: protect a
  route by role/permission, check inside a controller or a Forge view,
  create a brand-new role end to end via the CLI — worked examples on top
  of the existing reference documentation.
- New `.agents/docs/resumo-executivo-2026-08-07.md` — a session-level
  executive summary (workspace reorg, English-only pass, plugin management,
  CRUD builder + its admin UI, the release cut, the benchmark, the fixes
  that followed it, and RBAC) for anyone — human or agent — resuming this
  work without re-reading every commit.
- **Functional RBAC**, not just a data model. `roles`/`permissions` tables
  existed before but had no enforcement layer — now: `Model.has_role(slug)`
  (mirroring the existing `has_permission`), a third fallback tier on
  `GateManager.allows()` (ability closure → policy → `user.has_permission()`
  → deny by default), `RequireRole`/`RequirePermission` middleware with
  parameterized route-middleware aliases (`role:admin`, `permission:manage-
  users` — `resolve_route_middleware` now splits `alias:param` and injects
  the parameter into the middleware's constructor), CLI (`role:list/create/
  grant`, `permission:list/create`, `user:assign-role`), and a minimal admin
  UI at `/admin/roles`/`/admin/permissions` (behind `role:admin` — the first
  real usage of the new middleware). Documented in new
  `documentation/authorization.md`.
- **The 3 seeded demo accounts are now the framework's official demo
  credentials**, documented in `README.md`: `user@craft.local` (role
  `user`), `tenant@craft.local` (role `tenant-manager`, new — was
  previously seeded with **zero roles**, a real gap; also drives
  `TenantMiddleware`'s per-schema isolation), `admin@craft.local` (role
  `admin`, `is_admin=True`). All three password `craft`. The 3-tier ladder
  (`user` → `tenant-manager` → `admin`) is intentional — the middle tier now
  demonstrates elevated-but-not-full-admin access via `manage-users`.

### Fixed

- `Kernel.resolve_route_middleware`: a bare parameterized alias used
  without its parameter (e.g. `"role"` instead of `"role:admin"`) raised a
  raw `TypeError` from the middleware's constructor instead of the
  intended, actionable `KeyError` — now caught and re-raised with a message
  telling the caller to use `alias:value`.
- **Cross-file test pollution**: `test_ai_native_subsystems`
  (`tests/test_framework.py`) replaced the shared `modules`/`translations`
  tables with reduced ad-hoc schemas to test DB-driven behavior, and never
  restored them — since the test database is session-scoped, every test
  file running after it (alphabetically, before `test_subsystems_
  persistence.py`'s own unrelated workaround kicked in) saw the broken
  schema. Surfaced by the new `test_rbac.py` failing only as part of the
  full suite, never in isolation — exactly the class of bug `CONTRIBUTING.md`
  asks every test file to be immune to. Fixed at the source: the test now
  restores both tables to their real migrated shape in a `finally` block.
- `app/Http/Middleware/TenantMiddleware.py`'s docstring had a broken,
  machine-specific `file:///d:/data/www/craft/...` doc link — fixed to a
  normal relative reference, matching every other file's `References:`
  style.

### Added

- **CRUD builder now generates a real admin UI by default**, not just a JSON
  API — closing the gap flagged in `.agents/docs/benchmark-2026-08-07.md` §5
  ("Django gives a free admin list+edit UI from a model; Craft only gave
  JSON"). `make crud <Entity>` now also generates: a list view
  (`resources/views/admin/<slug>/index.forge.py`, paginated, with the same
  empty-state pattern `posts/index.forge.py` uses), a create/edit form
  (`admin/<slug>/{create,edit}.forge.py`, one input per field typed to match
  the field's DDL type, CSRF, validation errors + `old()`-preserved input on
  failure — same redisplay pattern the posts fix added), and a dedicated
  HTML controller (`app/Http/Controllers/Admin/<Entity>AdminController.py`)
  registered under `/admin/<slug>` behind `auth` middleware in `routes/web.py`
  — separate from, and non-colliding with, the existing JSON API controller
  and route in `routes/api.py`. Both can coexist for the same entity.

### Security

- CRUD-builder-generated write routes (`store`/`update`/`destroy`) had no
  authentication or authorization at all — `write_middleware="api"` alone
  never rejects a missing/invalid token (`AuthenticateApiToken` only
  resolves a user if present, it doesn't gate). Generated routes now use
  `write_middleware=["api", "auth"]`, and the generated `FormRequest.
  authorize()` checks for an authenticated user instead of always returning
  `True`. Anyone who ran `make crud` before this fix has a public
  read/write/delete API for that entity — regenerate or add auth manually.
- Mass-assignment protection was inverted: an undeclared/empty `fillable`
  meant *no* filtering, not full protection. `Model.create()`/
  `update_attributes()` now fail closed — nothing is mass-assignable unless
  `fillable` lists it or the model opts out with `guarded = False`.
- Added `SecurityHeaders` middleware (`X-Content-Type-Options: nosniff`,
  `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`),
  registered first in the default `bootstrap/app.py` stack. HSTS/CSP left
  opt-in — they need per-app tuning.
- `APP_KEY` empty in `APP_ENV=production` now fails startup loudly instead
  of silently falling back to a per-process ephemeral signing key (which
  broke sessions across restarts/workers without ever surfacing as an
  error). Non-production environments keep the ephemeral fallback.
- `docker-compose.prod.yml` no longer defaults `DB_PASSWORD` to the literal
  `secretpassword` — unset now fails the compose file loudly instead of
  silently shipping a known password. `docker-compose.yml` (dev) unchanged.
- `SECURITY.md`'s "Known gaps" section falsely claimed "no rate limiting on
  authentication endpoints" — `ThrottleRequests` is implemented and wired to
  `/login`/`/register`; corrected.

### Fixed

- `/admin` rendered a hardcoded `<h1>Admin Dashboard</h1>` instead of the
  real, styled `admin.dashboard` template that already existed in the repo.
  `HomeController.admin()` now fetches tenants/users and renders it.
- The demo blog (`PostController.store`/`update`) let a validation failure
  fall through to the generic exception handler, losing all typed input and
  showing an unstyled error fragment. Now redisplays the form with errors
  and preserved input, via a newly-wired `_old_input` session flash (the
  `old()` view helper existed but nothing populated it).
- CRUD-builder form lost all entered field rows on a server-side validation
  failure (only the entity name was preserved) and its dynamically-added
  field-row inputs had no `<label>` elements. Both fixed.
- `paginate()` had no maximum `per_page` — `?per_page=999999` was honored
  as-is. Capped to 100.
- `.agents/skills/framework/craft-development/SKILL.md` still claimed the ORM
  "wraps SQLAlchemy 2.0 Core" — missed by the earlier documentation audit
  because it lives outside `data/`. It's a custom query builder over
  `sqlite3`/`psycopg2`/`PyMySQL`; no SQLAlchemy, no Pydantic.

### Changed

- CI now matches what `CONTRIBUTING.md` already asked of a human: the
  suite runs against Python 3.11/3.12/3.13 (matrix) **and** against a real
  PostgreSQL service container, not SQLite only. Added `ruff check .`
  (non-blocking for now) and coverage reporting (`pytest-cov`,
  `--cov=services --cov-report=term-missing`) to CI output.
- `Dockerfile.prod` had stale "Codepy" branding (`addgroup/adduser codepy`)
  left over from before the framework's rename — now `dev`, matching
  `documentation/deployment.md`. Its `CMD` now runs `python dev.py migrate`
  (non-destructive) before starting gunicorn, since the prior boot sequence
  would serve against an unmigrated schema on a fresh deploy.
- `public/css/app.css`'s design tokens now alias the canonical `--craft-*`
  custom properties from `craft-theme.css` instead of redeclaring a
  near-duplicate palette — was a real footgun for anyone re-theming the app.
  `posts/show.forge.py`'s orphaned unstyled classes replaced with the
  utility classes the rest of `posts/*.forge.py` already uses.
- `.agents/docs/dx_and_ai_learning_curve.md` referenced a `.ai/` directory
  that doesn't exist (it's `.agents/`) and had a malformed comparison table
  with orphaned placeholder cells — fixed the path references, replaced the
  table with an accurate prose summary.

### Added

- `ruff` and `pytest-cov` added to the `[dev]` extra in `pyproject.toml`,
  with a deliberately small starting lint ruleset scoped to `services/`
  only (`E9`, `F`, `B`) — widen incrementally rather than false-starting a
  full-codebase style pass in one go.

### Not fixed — deliberately deferred

- **The concurrency ceiling measured in `.agents/docs/benchmark-2026-08-07.md`
  §1 is still there.** A real load test showed throughput flat at ~30 req/s
  regardless of concurrency (fully serialized). Root cause: sync dispatch on
  the event loop + a single shared `psycopg2` connection + no multi-worker
  option, and the three have to be fixed together — offloading sync work to
  a thread pool without first fixing the connection would corrupt concurrent
  cursor state. An attempt this session to add connection pooling found the
  fix isn't a local swap: `Connection` conflates the raw driver connection
  with mutable per-request session state (transaction depth, active tenant
  schema), so a real fix needs request-scoped connection lifecycle — new
  work touching `DatabaseManager`, `Connection`, tenant middleware, the
  migrator, and `conftest.py`, not a contained change. Stopped rather than
  ship something that passes tests today and breaks under real concurrency
  tomorrow — exactly the "degrades silently to something plausible" failure
  mode this project has been burned by before. This needs its own dedicated
  fatia with room to get the design right.

- Every change to the framework now requires a `CHANGELOG.md` entry in the
  same commit that makes it (not batched for the release cut) — policy
  documented in `CONTRIBUTING.md` ("Every change gets a CHANGELOG entry") and
  in `.agents/skills/framework/craft-development/SKILL.md` §3, so both human
  contributors and AI agents working in this repo pick it up.
- Codified: all code, orientation comments, and docstrings under `data/` are
  100% English, no exceptions — other languages enter only through the
  translation layer (`resources/lang/catalog.json`, `TranslationSeeder`,
  `__()`). Documented in `.agents/skills/framework/craft-development/SKILL.md`
  §2, with the grep check to run before finishing any change.

### Removed

- Four orphaned Portuguese view files from the already-supposedly-removed
  SoftPax domain, found to still be sitting in the tree: `resources/views/
  access/index.forge.py`, `resources/views/dashboard/index.forge.py`,
  `resources/views/admin/translations/index.forge.py`, and `resources/views/
  layout.py`. None were referenced by any controller, route, or test —
  confirmed via `self.view(...)`/`extends(...)` grep before deleting.

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
