# Changelog

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: `MAJOR.MINOR.PATCH` plus a release counter (`rNNNNN`) that
increments on every cut release, tracked in `engine/__init__.py`
(`__version__`, `__release__`) and `pyproject.toml`.

**Every change to `engine/`, `app/`, `bootstrap/`, `config/`, `database/`,
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

### Security

- **The panel showed an ordinary account how access is configured.** Its first
  revision gave every signed-in visitor a "My access" page listing permission
  slugs, the path each grant arrives by (`role`, `group-role`, `group`) and the
  raw ABAC conditions, plus role/group/permission counts on the dashboard and
  the account's `type` and `is_admin` on the profile. That is the
  installation's security configuration, not the visitor's personal data:
  knowing which roles exist and which of them you hold is a map for probing the
  system. The page is now the **access audit** at `role:admin`, the security
  rows on the profile are administrator-only, and the dashboard shows an
  ordinary account only what it wrote and when it joined. Reported from a
  running installation — the same way the `/admin` hole was.
- **`GET /admin` was readable by any authenticated user.** The dashboard lists
  every user, every administrator and every tenant in the installation, and it
  carried the `auth` alias alone — so the seeded `user@craft.local`, or any
  account that could log in, read the whole directory. Every *other* admin
  route already required `role:admin`; this one was missed. Reported from a
  running installation, not found by a test, which is the part worth keeping in
  mind. Three changes:
  - the route now declares `auth` + `role:admin`;
  - the controller repeats the check itself
    (`Gate.authorize("access-admin-dashboard")`, defined in
    `AuthServiceProvider` as `is_admin` OR the `admin` role) — two independent
    controls, because with the data this action returns, one forgotten alias
    must not be the only thing between an ordinary user and the installation;
  - `tests/test_admin_authorization.py` reproduces the report **and** adds a
    structural guard: every route under `/admin` must declare an authorizing
    alias (`role:`, `permission:`, `group:`, `can:`), not just `auth`. The page
    was not left open by a wrong decision — it was left open by a declaration
    nobody compared against its neighbours, and comparison by eye is not a
    control. A second test asserts each admin page still renders **200** for an
    administrator, since "locked down" and "broken" look identical from outside.
- **`has_role()` and `has_permission()` could not see group grants**, because
  they queried `role_user`/`permission_role` directly. With groups added, that
  would have meant membership looking correct in the admin UI while the route
  middleware refused. Both now delegate to the single resolver.
- **`AuthenticateApiToken` never rejected anything.** It resolved a user when a
  bearer token happened to match and called the next handler regardless, so
  every route carrying the `api` alias — including `routes/api.py`, whose own
  comment promised "writes require a valid API token", and every write route
  the CRUD builder generates — accepted anonymous callers. It now raises
  `AuthorizationException` for a missing *or* invalid token, with an identical
  response for both so probing cannot confirm which tokens exist. Covered by
  `tests/test_api_token_middleware.py`, which had no runtime counterpart before
  — the reason the gap survived.
- **The `api` guard had no column behind it.** `config/auth.py` declares
  `guards.api.token_name = "api_token"` and the middleware queried it, but no
  migration ever created it, so bearer-token authentication could not have
  succeeded for anyone. Added by
  `2026_08_10_000001_add_api_token_to_users.py`, nullable with a unique index.
- **`/admin/crud-builder` was protected by `auth` alone.** The builder writes
  real `.py` files into `app/` and `database/migrations/` and rewrites
  `routes/api.py` and `routes/web.py`, so any registered user — not just an
  admin — could execute code on the host. Now carries `role:admin`, matching
  the rest of the admin surface.
- **`make policy` generated a policy that authorized everyone.** Every ability
  returned `True`, including for `user=None`, so registering a generated policy
  produced a file that looked like protection while granting universal access.
  The stub now fails closed.
- **Aggregate columns bypassed the identifier allowlist.** `count`, `sum`,
  `avg`, `max` and `min` interpolated their column argument straight into SQL —
  the one hole in the defence every other clause in the query builder applies,
  and `count(request.input("col"))` is an ordinary-looking way to reach it.
- **`unique` and `exists` failed open.** Both wrapped their query in
  `except Exception: return`, so *any* database error made the rule pass: a
  typo'd table (`unique:userz,email`), an incompatible column type or a
  connection blip all validated cleanly and let the duplicate through. Only
  "no application booted" is tolerated now; a real query failure surfaces.
  Their table and column arguments also go through the identifier allowlist,
  since both are interpolated into SQL.

### Fixed

- **The Docker images still copied `services/`,** the package directory that
  the `engine/` rename replaced, so `docker compose up --build` failed outright
  on both `Dockerfile` and `Dockerfile.prod` — the dev container that was still
  running had simply never been rebuilt, and its bind mount pointed at the old
  workspace path. Both now copy `engine/`, and `docker-compose.yml` no longer
  claims the directory is called "craft framework".
- **`engine/orm/__init__.py` was empty** — the one subpackage in the engine
  that exported nothing, so `from craft.orm import Model`, exactly as
  `documentation/orm.md` teaches it, raised ImportError. It now exports `Model`,
  `QueryBuilder`, `DatabaseManager`, `Connection`, `Row`, `SoftDeletes`, the
  four relation classes and the four ORM exceptions, with a test asserting that
  every name in `__all__` resolves.
- **A route declared with `.module(...)` cost a SELECT per request.** The
  kernel queried the `modules` table inline on every hit, with no cache, and
  duplicated logic that already lived in `ModuleManager`. It now asks the
  manager, which caches state for `cache_ttl` (5s) and drops the entry
  immediately on `enable()`/`disable()`. `ModuleManager.state()` is new and
  returns `None` for a module it has never heard of — distinct from `False`,
  so the router can still fall back to `modules.<slug>.enabled` in config
  instead of 404ing an unregistered module. Query counts are asserted in
  `tests/test_module_state_cache.py`; write to the `modules` table behind the
  manager's back and you must call `forget_cached_state()`.
- **`PostController.show()`/`update()` returned a bare `PostResource`** while
  `store()` returned `.response()` — the same controller shaping its JSON two
  different ways. Both now go through `.response()`.
- **Three config keys nothing ever read.** `APP_URL` is now honoured by the new
  `Router.absolute_url_for()`; `auth.defaults.guard` and each guard's
  `provider` key now actually select the user model, via the new
  `AuthManager.provider_name()` (the model was previously read straight from
  `auth.providers.users.model`, so both keys were decorative). `APP_TIMEZONE`
  and `auth.password_timeout` were **removed** rather than left as knobs with
  no wiring: Craft writes every timestamp in UTC by design, and there is no
  confirm-password window to time out. Covered in
  `tests/test_placebo_regressions.py`.
- **`Auth.once()` authenticated nobody.** It was `validate(...) is not None`,
  so after a `True` return `Auth.check()` was still False, `Auth.user()` still
  None and `@auth` still saw a guest — `validate()` under a name that promises
  a login. It now sets the user for the current request while still writing
  nothing to the session, which is what "without persisting" means. The test
  covering it had asserted `guest() is True` afterwards, pinning the bug
  rather than the contract.
- **`@yield("title", "default")` leaked its quotes into the HTML.** The default
  was emitted raw, so the literal rendered as `"default"`, quotes included —
  `@section` already unwrapped literals correctly; `@yield` did not.
- **HTML form method spoofing never worked.** The framework emitted the hidden
  `_method` field from two places — the `@method("PUT")` view directive and
  every edit/delete form the CRUD builder generates — and read it back from
  none. Browsers only send GET and POST, so a `Route.resource()` update (PUT)
  or destroy (DELETE) received a POST and returned 405: the directive produced
  decorative HTML and generated admin forms did not work at all. The override
  is now applied at the ASGI layer, before Starlette matches on the method,
  since anything later is already too late. Only PUT/PATCH/DELETE may be
  spoofed — allowing `GET` would turn a write into a read and skip CSRF
  verification — and only for form encodings, so a JSON API cannot have its
  verb rewritten by a field that happens to carry that name.
- **`url_for()` invented URLs for routes that do not exist.** An unknown name
  returned the literal path `/{name}`, so `route("posts.index")` rendered the
  dead link `/posts.index`; the template helper then caught the failure and
  returned `"/"`, turning a typo into a link to the homepage. Both now raise.
- **`craft.support.view()` turned every template error into a fake success.**
  It caught all exceptions and returned `"View {name} rendered"` with HTTP
  200, so a missing template, a syntax error or an undefined variable produced
  a page that looked like it had worked. The same placebo had already been
  removed from `Controller.view` and the view engine; this copy was missed,
  and `DocsController` routed through it. Errors now reach the exception
  handler.
- **`Model.roles()/permissions()/has_role()/has_permission()` lived on the base
  model**, hardwired to `role_user.user_id` — so `Post.find(1).roles()`
  returned the roles of *user* 1: wrong data, no error. They moved to the
  models they describe (`User`, `Role`), which also removes the framework's
  import of `app.Models.Role`.
- **`Schema.table()` silently discarded indexes and constraints.** Only the
  `ADD COLUMN` was compiled, so `.indexed()`, `index()` and `unique_index()`
  were accepted on an existing table and never created — the migration read
  correctly and the index did not exist.
- **`enum()` enforced nothing.** It emitted a plain `VARCHAR(255)` and stored
  the allowed values in `Column.comment`, which no grammar reads. It now
  compiles a `CHECK (col IN (…))` constraint, portable across all three
  supported drivers.
- **A failed column probe was cached forever.** `table_has_column()` memoised
  an exception as "this table has no columns" for the life of the process,
  which quietly switched off every column-conditional feature — including the
  public UUID the ORM advertises, whose backfill simply stopped.
- **`SoftDeletes` listed after `Model` now raises instead of silently hard
  deleting.** The base order was a documentation footnote, but getting it
  wrong makes `delete()` destroy rows through a call the developer believes is
  reversible.
- **`SettingManager.set()` reported nothing.** It returned `None` whether the
  value was persisted or fell through to an in-memory dict that dies with the
  process; it now returns whether the write landed, and warns when it did not.
- **The admin dashboard rendered healthy with the database down.** Each query
  was wrapped in `except: []`, so an unreachable database produced a dashboard
  reporting zero of everything — indistinguishable from a correct answer.
- **`QueryBuilder` fell back to a default `DatabaseManager()`** when the
  container failed, running queries against a different connection than the
  application's rather than failing.
- **The task scheduler was a placebo.** `schedule` resolved to a nested stub
  class whose `hourly()`/`daily()` returned `self` and which never executed
  anything, while the `Schedule` facade was public and `CRAFT_DESIGN.md`
  documented a full cron-style scheduler. Replaced by a real
  `engine/schedule/` — a cron-expression matcher backing every frequency
  helper (`hourly`, `daily_at`, `every_fifteen_minutes`, `weekdays`, `cron`,
  …), `when`/`skip` constraints, and `without_overlapping()` locking so a task
  slower than its interval cannot stack copies of itself. Run it with
  `dev.py schedule run` from cron, or `dev.py schedule work` in the foreground;
  `dev.py schedule list` shows the registry.
- **Scheduled tasks were never registered.** Nothing called
  `register_console()`, so every task declared in `routes/console.py` was dead
  on arrival — the scheduler could not have run them even once it worked. The
  framework now imports it at boot, logging rather than silencing a broken
  console file.
- **Debug mode never turned on.** `ExceptionHandler` read `app.debug` and
  `dev.py about` read `app.env`/`app.debug`, but the config repository keys
  entries by the module attribute name, so those never resolved and both
  silently reported the default. They now read `app.APP_DEBUG` / `app.APP_ENV`,
  the names the kernel already used correctly.
- **The cache degraded silently.** An unrecognised `CACHE_DRIVER` (the shipped
  default, `memory`, was not one of the two names the resolver knew) and an
  unreachable Redis both fell back to an in-memory store with no signal —
  making rate limiting per-process, so a brute-force limit quietly multiplied
  by the worker count. `memory`/`array` are now recognised explicitly, and both
  fallbacks warn.
- **`dev.py schedule work` skipped the first minute**, sleeping before its
  first evaluation instead of after.

### Added

- **A control panel at `/panel`, for every signed-in account.** The skeleton
  had an icon-only rail whose labels appeared on hover — over the page content,
  which the expanded rail covered — and a menu hardcoded in the template with
  no relation to the visitor. Hardcoding it made the navigation a second,
  silent authorization system, which is how an ordinary account came to be
  shown a Dashboard button that led straight to a 403.
  - **`engine/support/navigation.py`** (new, bound as `nav`, `Nav` facade) is
    the menu as data. Each item declares the same guard as the route it points
    at — `permission`, `role`, `group`, `ability`, `module`, or a predicate —
    and `Nav.for_user(user, path)` returns only what that visitor may reach.
    Sections with no visible items disappear, so nobody stares at an empty
    "System" heading. Any error while evaluating an item hides it: a menu is
    not the place to be optimistic.
  - The shell (`layouts/panel.forge.py`) has a labelled sidebar, offsets the
    content by its width instead of covering it, and slides in as a drawer on
    small screens with no JavaScript.
  - Eight pages: dashboard, profile, posts, users, access audit, modules
    (enable/disable, POST + CSRF), plugins, and an "about this install" read
    from the running application rather than a config file.
  - The panel is **not** an admin area — an ordinary account gets a real
    workspace, an administrator sees the same shell with more sections in it.
    Building two panels is how the two drift apart.
  - Fixed while looking at the running page, not by a test: `/panel` lit up
    alongside `/panel/access`, because per-item prefix matching cannot express
    "closest wins". Exactly one item is active now, chosen across the whole menu.
- **Groups and attribute-based access control (ABAC).** Authorization could
  previously say only *who you are*: a user held roles, and roles held
  permissions. Two things real systems need were missing.
  - **Groups** (`groups`, `group_user`, `group_role`, `permission_group`) grant
    access to a team rather than one person at a time: a group carries roles
    and/or permissions and every member inherits them, so onboarding is one
    membership row. Plus `permission_user` for the case every system hits
    eventually — one person, one extra permission, where inventing a
    single-member role is worse than recording it honestly.
  - **Conditions** — every grant table carries a nullable `conditions` column
    holding a small JSON object evaluated against the record being acted upon:
    `{"user_id": "@user.id"}` for *only your own*, `{"amount": {"lte": 10000}}`
    for an approval ceiling. `@user.<attr>` resolves to the acting user.
    Operators: eq, ne, in, not_in, gt, gte, lt, lte, is_null, contains. `NULL`
    means unconditional, so every existing grant keeps working untouched.
  - **`engine/auth/access.py`** is now the single place that answers "can this
    user do this?", unioning all four grant paths (direct, role, group→role,
    group) in one query. `has_role`, `has_permission` and the new `can()` on
    `User` delegate to it; the Gate consults it after closures and policies and
    passes the resource through, so a conditional grant is evaluated rather
    than treated as unconditional.
  - Three deliberate behaviours, each failing safe: `has_permission()` (no
    resource) counts **unconditional grants only**, since answering True for a
    narrowed grant would widen it; a **malformed condition denies** and is
    logged, so a typo cannot become an open grant; and `{}` is not `NULL` —
    someone wrote it and meant something, so it denies.
  - Exposed everywhere it needs to be: the `group:<slug>` route middleware, an
    `Access` facade (`roles`, `groups`, `permissions`, `explain`), the
    `/admin/groups` screen (membership, role grants, permission grants with
    conditions shown verbatim), and CLI — `group create|list|add-user|
    remove-user|grant-role|grant`, `user grant --conditions`, and
    `user access <email>`, which prints why each permission reaches someone.
  - The seeder ships a working example rather than empty tables: a
    `content-team` group granting the `user` role, and one conditional grant
    (the team may `publish-post`, but only their own) so the feature is visible
    and not merely documented.
  - `documentation/authorization.md` rewritten around all of it.
- **Every Forge view now carries a documentation header** — what the page is,
  which controller and route render it, what guards it, and the context
  variables it expects. 16 of 16.
- **`CRAFT_ENGINE.md`** — the framework's own overview, written for whoever (or
  whatever) picks this repository up cold: what each engine subsystem provides,
  the build loop for a feature, and how the same codebase carries an
  application through four stages — a single-machine blog, a real product with
  roles and background work, a concurrent multi-worker deployment, and
  schema-per-tenant multi-tenancy. It carries an explicit **"what does not
  exist yet"** section (storage/S3, mail, API key manager, Redis queue driver,
  broadcasting, nested eager loading, remember-me, session encryption), because
  an agent that assumes those exist writes code that cannot work. Linked from
  both READMEs and the documentation index.
- **The framework serves requests in parallel.** Throughput was ~27 req/s
  whether 1 client or 50 were connected — the signature of a process handling
  one request at a time — and p95 latency at 50 clients was 1.9s. It is now
  ~115 req/s from 10 clients up, with p95 at 0.57s and no failed requests.
  Measured on the sample app with `tools/loadtest.py` (new, standard library
  only), before and after, by toggling only the offload. Three changes, in the
  order the backlog required, because doing them in any other order corrupts
  state under real load:
  1. **A bounded connection pool** (`engine/orm/connection.py`). A `Connection`
     held one raw DB-API handle plus mutable per-request state, so two threads
     would have shared a cursor. A thread now checks a connection out on first
     use and returns it at the end of the request; `pool_size` (default 10) and
     `pool_timeout` (default 30s) are per-connection config. Exhaustion raises
     an error naming the setting instead of hanging. Per-thread connections
     *without* the release boundary were tried first and are not a pool — they
     accumulate one per thread until PostgreSQL answers "too many clients
     already", which is exactly what the suite did.
  2. **Per-request state moved off the singletons.** Transaction depth and the
     tenant `search_path` now belong to the borrowed connection, and
     `AuthManager`'s current user/session are thread-local. Both were
     process-wide, which under concurrency is not a race but a correctness
     hole: one tenant's request could repoint the schema mid-query of another's,
     and one visitor's identity could be read on another visitor's request.
     `DatabaseManager.release()` also clears the tenant, so a recycled thread
     never inherits the previous request's tenant.
  3. **The kernel offloads to the thread pool** (`run_in_threadpool`), and
     releases the connection inside the worker thread that borrowed it.
  Covered by `tests/test_connection_concurrency.py` — real threads asserting
  session isolation, transaction-depth isolation, tenant-schema isolation on
  live PostgreSQL, identity isolation, pool reuse, bounded growth, exhaustion
  and rollback of an abandoned transaction on release.
- **`dev.py serve --workers N`** for multiple processes. It refuses to pretend:
  `--workers` with `--reload` is impossible in uvicorn, so it says so and
  serves with one instead of silently ignoring the flag.
- **`ruff check .` now fails the build.** CI ran it as `ruff check . || true`,
  the same placebo pattern applied to the pipeline: the lint could never
  reprove anything. The nine findings it had been hiding are fixed (six
  `raise ... from None` in the CLI, an unused loop variable, a constant
  `getattr`, and a `zip()` without `strict=`), so the guard is now on with a
  clean base. The `zip(..., strict=True)` in `engine/orm/connection.py` is
  deliberate: a row whose arity disagrees with `cursor.description` is a driver
  bug, and pairing them off silently would drop columns. Validated on SQLite
  and on real PostgreSQL.
- **`documentation/orm.md` gained the eager-loading and soft-deletes sections**
  the index had been promising, plus many-to-many. `resources.md:133` already
  linked to `orm.md#eager-loading`, which did not exist. The sections state the
  current limit explicitly (one level; no nested `with_("posts.comments")`, no
  `collection.load()`, no `with_count()`) and document the `SoftDeletes` MRO
  trap that now raises `TypeError`. `crud-builder.md` was an orphan — it is in
  the index now, and the broken `orm.md#query-builder` anchor was corrected.
- **The event bus and the plugin hook system now actually run.** Both were
  fully implemented and unit-tested, but nothing in the framework ever emitted
  an event or triggered a hook — in a running application both subsystems were
  inert. Three things closed the gap:
  - `engine/events/lifecycle.py` (new) defines the framework's own events —
    `model.created` / `model.updated` / `model.deleted`, and `auth.login` /
    `auth.failed` / `auth.logout` — plus a `fire()` helper that no-ops when no
    container is bound (models are used in unit tests with no booted app) and
    logs rather than raises when a listener misbehaves, so a third-party
    listener cannot turn a successful INSERT into a request error.
  - `engine/orm/model.py` and `engine/auth/manager.py` emit them at the write
    and authentication points. `UserLoginFailed` carries the identifier only —
    never the submitted password, which would otherwise reach every listener
    and plugin and anything they log.
  - `PluginManager.bridge_events()` registers the manager as a *wildcard*
    listener and forwards each event to hooks registered under its `name`, so
    there is one emission point per lifecycle event rather than two dispatch
    paths to keep in sync. `PluginManager.load_enabled()` imports enabled
    plugins and calls their `register(app)` — previously nothing ever imported
    a plugin's code, so no hook could ever be added.
- **Bundled `audit-log` plugin** (`plugins/audit-log/`) — the first plugin with
  real logic, writing an audit trail of model writes and authentication to
  `system_logs`. It skips its own table: auditing `system_logs` would make each
  write emit `model.created`, which writes another row, forever. Any plugin
  persisting from inside a model hook needs the same guard.

### Changed

- **The framework package was renamed `services/` → `engine/`.** The public
  import alias is unchanged: application code still writes `from craft.…`,
  which `engine/__init__.py` installs via its meta path finder. Only the
  on-disk directory moved. Every internal import, `pyproject.toml`
  (`dev = "engine.cli.app:main"`, packaging and ruff includes), the CI
  coverage target (`--cov=engine`), the entrypoints (`dev.py`,
  `bootstrap/app.py`, `public/index.py`, `config/app.py`), the test suite,
  and the documentation were updated to match. The rename had left the tree
  in a non-booting state — files were moved but no import followed them.

### Fixed

- **The 3 seeded demo accounts were all created as identical non-admin
  users.** `UserSeeder` created them through `Model.create()`, which enforces
  `fillable`; since `type` and `is_admin` are deliberately excluded from
  `User.fillable` (so request input can never escalate privileges), both
  columns were silently dropped. `admin@craft.local` had `is_admin = False`
  and `tenant@craft.local` had `type = "user"`, which meant the admin surface
  and `TenantMiddleware` never saw the accounts the docs describe as the
  framework's official demo ladder. The seeder now uses the trusted
  `force_create` path, and password hashing moved from `User.create` to
  `User.force_create` so *every* insert path hashes rather than only the
  mass-assignment-filtered one. Regression test asserts `type`, `is_admin`,
  and that the documented password authenticates
  (`tests/test_rbac.py::test_demo_users_get_their_privilege_columns`) — the
  previous test asserted roles only, which is why this went unnoticed.

- **Hero background was boxed inside a box, still not full width.**
  `layouts/app.forge.py` wraps every public page's content in `max-w-7xl
  mx-auto` (1280px); `.hero-section` then had its own nested `max-width:
  1120px` on top of that, so the hero's gradient background never reached
  the real viewport edges — visibly boxed with large empty gutters on wide
  screens, which is what the previous "two columns" fix alone didn't
  address. Split the hero into two layers, matching the pattern every
  other section on the page already uses (a full-width band +
  `.section-container` inside it): `.hero-section` now breaks out of its
  ancestor's max-width with the standard full-bleed technique
  (`margin-inline: calc(50% - 50vw)`) so its background spans the true
  viewport width; the actual two-column content grid moved to a new
  `.hero-inner` (`resources/views/home.forge.py`), capped at a readable
  1120px and centered, same as before. The full-bleed technique's known
  side effect — `vw` units include the scrollbar's width on most browsers,
  which produced a few pixels of horizontal overflow — is clamped with
  `overflow-x: hidden` on `body` (the standard fix, not a workaround).
  Verified live at 1920px (background reaches both edges, content stays
  readable), 1440px, and 390px (unchanged mobile stack).
- **Hero section on the landing page was never actually two columns.**
  `.hero-section` was `flex-direction: column` unconditionally — copy and
  the code preview always stacked, centered, at every viewport width, which
  is what made the page feel like it never used the screen's width. Now a
  real CSS grid: single column below 1024px (unchanged mobile behavior),
  two columns (copy left, code preview right) at 1024px+. Verified live
  with a headless browser at 1440px (two columns), 390px (stacked), and
  with `prefers-color-scheme: dark` (surfaced an unrelated bug, next entry).
- **Landing page was unreadable on a system with dark mode on.**
  `craft-components.css`'s `--bg-body`/`--bg-section` aliased to the
  semantic `--craft-bg`/`--craft-surface` tokens, which correctly flip dark
  under `prefers-color-scheme: dark` (that's how `craft-theme.css` is
  designed to work) — but every text color on the landing page
  (`--slate-700/800/900`) is a literal, never-swapping step chosen
  assuming a light background. Background went dark, text didn't: several
  sections rendered dark text on a near-black ground, unreadable. Pinned
  `--bg-body`/`--bg-section` to the literal light slate steps instead — the
  landing page now commits to a single light presentation on purpose,
  rather than a half-finished dark mode with broken contrast. Verified live
  with `prefers-color-scheme: dark` forced on: background now stays light
  end to end.
- **The earlier "unified CSS design tokens" fix (this file, same session,
  under "Changed") edited the wrong file.** `public/css/app.css` — which
  that fix touched — was never linked from any view; the landing page
  actually loads `assets/css/craft-components.css`, an near-identical but
  separate copy. The dead file is now deleted; today's hero fix (and any
  future landing-page CSS change) targets `craft-components.css`, the one
  actually served. A lesson for next time: a CSS/UI fix isn't verified by
  `pytest` passing — none of these tests render a page — it needs an actual
  browser check, which is what caught this.

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
