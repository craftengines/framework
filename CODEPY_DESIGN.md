# Codepy Framework — Architectural Design Blueprint

> A expressive backend framework built in pure Python on FastAPI, with PostgreSQL as the native database.

---

## Table of Contents

1. [High-Level Architecture Overview](#1-high-level-architecture-overview)
2. [Folder Structure](#2-folder-structure)
3. [MVC Pattern Adapted to FastAPI](#3-mvc-pattern-adapted-to-fastapi)
4. [Service Container & Service Providers](#4-service-container--service-providers)
5. [Middleware Pipeline Architecture](#5-middleware-pipeline-architecture)
6. [Routing System](#6-routing-system)
7. [ORM Design (Codepyquent)](#7-orm-design-codepyquent)
8. [Migration System](#8-migration-system)
9. [Validation Layer](#9-validation-layer)
10. [Authentication & Authorization](#10-authentication--authorization)
11. [Events, Listeners, Jobs & Queues](#11-events-listeners-jobs--queues)
12. [Task Scheduling System](#12-task-scheduling-system)
13. [CLI Tool Design](#13-cli-tool-design)
14. [Configuration System](#14-configuration-system)
15. [Exception Handling Architecture](#15-exception-handling-architecture)
16. [Template Engine Integration](#16-template-engine-integration)
17. [Modular Package Structure](#17-modular-package-structure)
18. [Developer Experience Principles](#18-developer-experience-principles)
19. [Additional Subsystems](#19-additional-subsystems)

---

## 1. High-Level Architecture Overview

Codepy is a full-stack backend framework that wraps FastAPI's ASGI runtime with the framework's architectural patterns. The framework is organized into layers, each with a single responsibility, communicating through a central inversion-of-control container.

### Layered Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLI (craft)                                  │
│                  make:* · migrate · serve · tinker                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐   ┌─────────────┐   ┌──────────┐   ┌────────────┐  │
│  │   Router    │──▶│  Middleware │──▶│Controller│──▶│  Response  │  │
│  │  (Dispatch) │   │  Pipeline   │   │ (Action)  │   │ (Renderer) │  │
│  └─────────────┘   └─────────────┘   └──────────┘   └────────────┘  │
│         │               │               │              ▲           │
│         │               │               │              │           │
│         ▼               ▼               ▼              │           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Service Container (IoC)                   │   │
│  │   bind · singleton · scoped · auto-resolve · contextual     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────┐  ┌──────────┐  ┌─────────┐  ┌────────┐  ┌──────────┐  │
│  │  ORM     │  │  Auth    │  │ Events  │  │ Queue  │  │  Config  │  │
│  │(Codepyquent)│  │ Guards  │  │Dispatch │  │Manager │  │Repository│  │
│  └──────────┘  └──────────┘  └─────────┘  └────────┘  └──────────┘  │
│       │                                                         │   │
│       ▼                                                         ▼   │
│  ┌──────────────────┐                              ┌────────────────┐│
│  │   PostgreSQL     │                              │  Forge Engine  ││
│  │ (via asyncpg /   │                              │ (Jinja2││
│  │  SQLAlchemy 2.0) │                              │  directives)   ││
│  └──────────────────┘                              └────────────────┘│
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                      ASGI Server (uvicorn)                           │
└─────────────────────────────────────────────────────────────────────┘
```

### Request Lifecycle

```
HTTP Request
    │
    ▼
┌──────────────────┐
│  ASGI Server      │  uvicorn receives HTTP request, passes to Starlette app
│  (uvicorn)        │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  HTTP Kernel     │  Bootstraps app, starts scoped container,
│                  │  wraps Starlette Request in Codepy Request
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Global          │  CORS, TrustHosts, SessionStarter, etc.
│  Middleware      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Router          │  Matches method + path → Route object
│  (Dispatch)      │  Extracts path parameters, resolves route middleware
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Route           │  Authenticate → VerifyCsrfToken → Authorize → ...
│  Middleware      │  → ... → Controller
│  Pipeline        │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Controller      │  Resolves dependencies from container
│  Action          │  Calls FormRequest.validate() if typed
│                  │  Invokes service layer / ORM
│                  │  Returns Response / dict / view / redirect
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Response        │  Converts CodepyResponse → Starlette Response
│  Renderer        │  Applies after-middleware (onion unwinding)
└────────┬─────────┘
         │
         ▼
    HTTP Response
```

### Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| ASGI framework | FastAPI / Starlette | Async-native, high performance, Pydantic integration |
| Database | PostgreSQL (default) | Supports JSONB, UUID, full-text search, advisory locks |
| DB driver | asyncpg (async) / psycopg (sync) | asyncpg for async path; psycopg3 for sync CLI/migrations |
| ORM style | Active Record | Familiar, terse for CRUD; wraps SQLAlchemy 2.0 Core for SQL generation |
| Template engine | Jinja2 extended as "Forge" | Mature, Python-native; extended with Forge directive preprocessor |
| CLI framework | Typer | Type-hint-driven, auto-generates help, Click-compatible |
| Validation | Custom rule engine on Pydantic v2 | Declarative rule DSL; Pydantic for schema enforcement |
| Config | Python files in `config/` | Type-safe, importable, env-merged at load time |

---

## 2. Folder Structure

The folder structure follows a conventional conventions exactly, adapted for Python packaging.

```
project/
├── app/                                # Application code
│   ├── Http/
│   │   ├── Controllers/
│   │   │   ├── HomeController.py
│   │   │   ├── PostController.py
│   │   │   └── AuthController.py
│   │   ├── Middleware/
│   │   │   ├── Authenticate.py
│   │   │   ├── EncryptCookies.py
│   │   │   ├── VerifyCsrfToken.py
│   │   │   ├── TrustProxies.py
│   │   │   └── StartSession.py
│   │   ├── Requests/                   # FormRequest validation classes
│   │   │   └── StorePostRequest.py
│   │   └── Resources/                  # API Resources (JSON transformers)
│   │       ├── PostResource.py
│   │       └── PostCollection.py
│   ├── Models/
│   │   ├── User.py
│   │   └── Post.py
│   ├── Policies/
│   │   └── PostPolicy.py
│   ├── Events/
│   │   └── PostPublished.py
│   ├── Listeners/
│   │   └── NotifySubscribers.py
│   ├── Jobs/
│   │   └── ProcessPodcast.py
│   ├── Mail/
│   │   └── WelcomeEmail.py
│   ├── Notifications/
│   │   └── PostPublishedNotification.py
│   ├── Services/                       # Domain service classes
│   │   └── PaymentService.py
│   ├── Providers/
│   │   ├── AppServiceProvider.py
│   │   ├── AuthServiceProvider.py
│   │   ├── EventServiceProvider.py
│   │   ├── RouteServiceProvider.py
│   │   └── BroadcastServiceProvider.py
│   ├── Console/
│   │   └── Commands/                   # Custom CLI commands
│   │       └── SendEmailsCommand.py
│   └── Exceptions/
│       └── Handler.py                  # App-specific exception handler
│
├── bootstrap/
│   └── app.py                          # Application factory (create_app)
│
├── config/                             # Configuration files (Python modules)
│   ├── app.py                          # App name, env, debug, key, timezone
│   ├── auth.py                         # Guards, providers, password settings
│   ├── cache.py                        # Cache stores: memory, file, redis
│   ├── database.py                     # Connections: pgsql (default), sqlite
│   ├── filesystems.py                  # Disk configurations
│   ├── logging.py                      # Log channels and stacks
│   ├── mail.py                         # Mail drivers: smtp, ses, postmark
│   ├── queue.py                        # Queue connections: sync, database, redis
│   ├── session.py                      # Session driver, lifetime, cookie
│   └── services.py                     # Service bindings
│
├── database/
│   ├── migrations/                     # Timestamped migration files
│   │   ├── 2025_01_01_000001_create_users_table.py
│   │   ├── 2025_01_01_000002_create_posts_table.py
│   │   └── 2025_01_01_000003_create_jobs_table.py
│   ├── seeders/                        # Database seeders
│   │   ├── DatabaseSeeder.py
│   │   ├── UserSeeder.py
│   │   └── PostSeeder.py
│   └── factories/                      # Model factories
│       └── UserFactory.py
│
├── resources/
│   ├── views/                          # Forge templates (.forge.py)
│   │   ├── layouts/
│   │   │   └── app.forge.py
│   │   ├── posts/
│   │   │   ├── index.forge.py
│   │   │   ├── show.forge.py
│   │   │   └── create.forge.py
│   │   └── auth/
│   │       ├── login.forge.py
│   │       └── register.forge.py
│   └── lang/                           # Localization files
│       └── en/
│           └── messages.py
│
├── routes/
│   ├── web.py                          # Web routes (session, CSRF)
│   ├── api.py                          # API routes (token, throttle)
│   └── console.py                      # Console routes (scheduled tasks)
│
├── storage/
│   ├── app/
│   │   └── public/                    # Public uploads
│   ├── logs/                           # Log files
│   └── framework/
│       ├── cache/                      # File cache
│       └── sessions/                   # File sessions
│
├── tests/
│   ├── Feature/                        # Feature tests (HTTP endpoints)
│   └── Unit/                           # Unit tests (models, services)
│
├── services/                           # Framework core engine (mapped to `codepy.*`)
│   ├── container/                      # DI container (bind, singleton, make)
│   ├── config/                         # Config repository & env()
│   ├── http/                           # HTTP kernel, router, middleware, response
│   ├── orm/                            # Codepyquent ORM & QueryBuilder
│   ├── validation/                     # Validator, FormRequest, Rule
│   ├── auth/                           # Guards, gates, policies
│   ├── events/                         # Event dispatcher
│   ├── queue/                          # Queue manager, jobs
│   ├── view/                           # Forge templating (directive parser)
│   ├── facades/                        # Facade base + concrete facades (FacadeMeta)
│   ├── providers/                      # Framework service providers
│   ├── exceptions/                     # Exception handler
│   ├── security/                       # PQC (Post-Quantum Security) & Captcha
│   ├── modules/                        # Dynamic module manager
│   ├── plugins/                        # Plugin manager
│   └── support/                        # Helpers (__(), view(), Collection)
│   ├── exceptions/                     # Exception handler, base exceptions
│   ├── cli/                            # CLI application + generators
│   ├── resources/                      # API Resource base classes
│   ├── seeding/                        # Seeder base
│   ├── factories/                      # Factory base
│   ├── cache/                          # Cache manager
│   ├── schedule/                       # Task scheduler
│   ├── broadcast/                      # Broadcasting (websockets)
│   ├── filesystem/                    # Filesystem manager
│   ├── mail/                           # Mail manager
│   ├── notification/                  # Notification channels
│   └── support/                        # Helper functions
│
├── craft.py                          # CLI entry point (python craft.py)
├── bootstrap.py                        # Bootstrap helper
├── pyproject.toml                      # Package metadata + dependencies
├── .env                                # Environment variables
└── .gitignore
```

---

## 3. MVC Pattern Adapted to FastAPI

### Conceptual Mapping

| Concept | Codepy (Python) | Notes |
|---|---|---|
| Controller class | Controller class extending `codepy.http.Controller` | Methods receive a `Request` and return a `Response` |
| Model | Codepyquent Model extending `codepy.orm.Model` | Active record with metaclass for table auto-discovery |
| Template view | Forge template (`.forge.py`) | Jinja2 preprocessed with Forge directives |
| Route file | `routes/web.py`, `routes/api.py` | Same file-based route registration |
| FormRequest | FormRequest extending `codepy.validation.FormRequest` | Validates and authorizes before controller |
| Middleware | Middleware extending `codepy.http.Middleware` | Onion-order pipeline |
| Service Provider | ServiceProvider extending `codepy.providers.ServiceProvider` | register() + boot() lifecycle |

### Controller Design

Controllers are plain Python classes. Each public method is a route action. The router resolves the controller from the container, instantiates it with dependency injection, and calls the action method with type-hinted parameters.

**Dependency injection**: The controller's `__init__` and action methods support type-hinted injection. The container inspects constructor and method signatures, resolves types from the container, and injects them.

**Return types**: Action methods may return:
- A `Response` object (explicit status, headers)
- A `dict` or `list` (auto-converted to JSON)
- A `str` (auto-converted to HTML)
- A `Resource` or `ResourceCollection` (serialized to JSON)
- A view render result (from `self.view()`)
- A redirect (from `self.redirect()`)
- `None` (204 No Content)

**FormRequest injection**: When an action method type-hints a `FormRequest` subclass as a parameter, the framework automatically:
1. Constructs the FormRequest from the current HTTP request
2. Calls `authorize()` — raises `AuthorizationException` if false
3. Calls `validate()` — raises `ValidationException` if rules fail
4. Passes the validated data to the controller method

### Model Design

Models are active-record classes. Each model:
- Auto-resolves its table name from the class name (CamelCase → snake_case → pluralized)
- Defines `fillable` (mass-assignable) and `hidden` (serialized out) attributes
- Supports `casts` for type coercion on get/set
- Supports accessor/mutator methods (`get_X_attribute` / `set_X_attribute`)
- Defines relationships as methods returning relationship descriptors
- Supports query scopes as class methods prefixed with `scope_`
- Supports soft deletes via a mixin

### View Design

Views are Forge templates (Jinja2 with Forge directives). The controller calls `self.view("posts.show", {"post": post})` which:
1. Resolves the template file (`posts/show.forge.py`)
2. Preprocesses Forge directives to Jinja2 syntax
3. Inlines `@extends` parent templates and `@include` partials
4. Injects global variables (auth user, csrf token, config, session, errors)
5. Renders to HTML and wraps in a `Response`

---

## 4. Service Container & Service Providers

### Service Container

The container is the heart of the framework. It is an inversion-of-control container that manages all class instantiation and dependency resolution.

**Binding types**:

| Method | Lifetime | Use Case |
|---|---|---|
| `bind(key, factory)` | New instance every resolve | Stateless services, request-scoped helpers |
| `singleton(key, factory)` | One instance per application | Database connection, config, router, cache |
| `scoped(key, factory)` | One instance per request | Request, session, auth guard, transaction |
| `instance(key, obj)` | Pre-built singleton | Pre-constructed objects |
| `alias(alias, key)` | Alias to another binding | Short names for long class paths |
| `tag(tags, key)` | Group bindings under tags | Event listeners, middleware groups |

**Resolution**: When `make(key)` is called:
1. Check if an existing instance is cached (singleton/instance)
2. Check if a scoped instance exists for the current request
3. If a factory is registered, call it with the container as argument
4. If no binding exists, attempt auto-resolution: inspect the class constructor, resolve each parameter by type hint from the container

**Auto-resolution**: For classes with no explicit binding, the container inspects `__init__` type hints and recursively resolves each parameter. This enables constructor injection without any registration.

**Contextual bindings**: A class can declare that when it depends on interface X, it wants a specific implementation. This follows a conventional `$this->app->when(PhotoController::class)->needs(Filesystem::class)->give(S3Filesystem::class)`.

### Service Providers

Service providers are the bootstrap mechanism. Every core subsystem and every application-level service is registered through a provider.

**Lifecycle**:

```
Application created
    │
    ▼
register_config()          ← Load config/*.py into Config repository
    │
    ▼
register_provider(P)       ← For each provider:
    │                         P.register() — bind services into container
    │                         Store provider instance
    ▼
Facade._app = app          ← Wire facades to the container
    │
    ▼
app.boot()                  ← For each provider:
    │                         P.boot() — perform post-registration logic
    ▼
Application ready
```

**Framework providers** (registered in `bootstrap/app.py`):

| Provider | Registers | Boots |
|---|---|---|
| `DatabaseServiceProvider` | `db` (DatabaseManager singleton) | Initializes connection pool |
| `RouterServiceProvider` | `router` (Router singleton) | — |
| `ViewServiceProvider` | `view` (Forge singleton) | Registers view namespaces |
| `AuthServiceProvider` | `auth` (AuthManager), `gate` (GateManager) | — |
| `EventServiceProvider` | `events` (EventDispatcher) | — |
| `QueueServiceProvider` | `queue` (QueueManager) | — |
| `LoggingServiceProvider` | `log` (logging.Logger) | Configures handlers |
| `CacheServiceProvider` | `cache` (CacheManager) | — |
| `MigratorServiceProvider` | `migrator` (Migrator), `schema` (SchemaFacade) | Registers migration paths |
| `ExceptionServiceProvider` | `exception_handler` (Handler) | — |
| `ScheduleServiceProvider` | `schedule` (ScheduleManager) | Registers scheduled tasks |
| `BroadcastServiceProvider` | `broadcast` (BroadcastManager) | — |
| `FilesystemServiceProvider` | `storage` (FilesystemManager) | — |
| `MailServiceProvider` | `mail` (MailManager) | — |
| `NotificationServiceProvider` | `notification` (NotificationManager) | — |

**Application providers** (registered in `bootstrap/app.py` after framework providers):

| Provider | Responsibility |
|---|---|
| `AppServiceProvider` | App-level bindings, service registration |
| `AuthServiceProvider` | Policy registration, gate definitions |
| `EventServiceProvider` | Event-to-listener mappings |
| `RouteServiceProvider` | Load route files (web, api, console) |
| `BroadcastServiceProvider` | Channel authorization callbacks |

### Deferred Providers

Providers can be "deferred" — their bindings are only registered when first resolved. This reduces boot time for rarely-used services. A deferred provider exposes a `provides()` method returning the list of container keys it registers. When `make(key)` is called for a deferred key, the provider is registered on-demand.

---

## 5. Middleware Pipeline Architecture

### Onion Model

Middleware runs in onion order: the first registered middleware executes first on the way in and last on the way out. Each middleware receives the request and a `next` callable. It performs pre-processing, calls `next(request)`, then performs post-processing on the response.

```
Request ──▶ MW1(before) ──▶ MW2(before) ──▶ MW3(before) ──▶ Controller
                                                                         │
Response ◀── MW1(after) ◀── MW2(after) ◀── MW3(after) ◀── Response ────────┘
```

### Middleware Categories

| Category | When it runs | Examples |
|---|---|---|
| **Global** | Every request, before route middleware | CORS, TrustProxies, StartSession, ShareErrorsFromSession, MaintenanceMode |
| **Group** | When a route belongs to a middleware group | `web` group: EncryptCookies, VerifyCsrfToken, StartSession; `api` group: ThrottleRequests, SubstituteBindings |
| **Route** | Specific routes via `Route.middleware()` | Authenticate, Authorize, CanCheck |

### Middleware Groups

Two default groups ship out of the box:

**`web` group**: EncryptCookies → VerifyCsrfToken → StartSession → ShareErrorsFromSession

**`api` group**: ThrottleRequests:60,1 → SubstituteBindings

Routes in `routes/web.py` automatically get the `web` group. Routes in `routes/api.py` get the `api` group.

### Middleware Aliases

Middleware can be referenced by short alias strings:

| Alias | Class |
|---|---|
| `auth` | Authenticate |
| `guest` | RedirectIfAuthenticated |
| `can` | Authorize (ability, model) |
| `throttle` | ThrottleRequests (max, decay) |
| `verified` | EnsureEmailIsVerified |
| `signed` | ValidateSignature |
| `csrf` | VerifyCsrfToken |

### Pipeline Execution

The HTTP Kernel constructs a `MiddlewarePipeline` with `[global_middleware + group_middleware + route_middleware]` and sends the request through it. The pipeline's destination is the route's controller action. The pipeline wraps each middleware around the next, so middleware execute in registration order on the way in and reverse order on the way out.

### Terminating Middleware

Some middleware (like `SendScheduledJobs`) perform work after the response is sent. These implement a `terminate(request, response)` method called after the response leaves the pipeline.

---

## 6. Routing System

### Route Registration

Routes are registered in `routes/web.py` and `routes/api.py` using the `Route` facade:

**HTTP verbs**: `Route.get()`, `Route.post()`, `Route.put()`, `Route.patch()`, `Route.delete()`, `Route.options()`, `Route.any()`, `Route.match()`.

**Action formats**:
- `[ControllerClass, "method_name"]` — array form (preferred)
- `"ControllerName.method_name"` — string form (resolved by import)
- `lambda request: ...` — closure form

### Route Groups

Groups share attributes across a set of routes:

**Attributes**: `prefix`, `middleware`, `namespace`, `name` (name prefix).

Groups can be nested. Each nested group inherits and merges parent attributes:
- `prefix`: concatenated with `/`
- `middleware`: merged in order
- `name`: concatenated (dot-separated)

### Named Routes

Every route can be named via `.name("route.name")`. Named routes are stored in a `_named` dict and resolved by `Route.url_for("name", **params)` which substitutes path parameters.

### Resource Routing

`Route.resource("posts", PostController)` registers 7 routes:

| Verb | URI | Method | Name |
|---|---|---|---|
| GET | `/posts` | index | posts.index |
| GET | `/posts/create` | create | posts.create |
| POST | `/posts` | store | posts.store |
| GET | `/posts/{post}` | show | posts.show |
| GET | `/posts/{post}/edit` | edit | posts.edit |
| PUT/PATCH | `/posts/{post}` | update | posts.update |
| DELETE | `/posts/{post}` | destroy | posts.destroy |

`Route.api_resource("posts", PostController)` registers only 5 (no create/edit HTML routes).

### Route Model Binding

Route parameters enclosed in `{braces}` are automatically bound:

**Implicit binding**: `{post}` → `Post.query().where("id", param).first()`. If the parameter name matches a registered model, the framework auto-resolves it.

**Explicit binding**: `Route.model("post", Post)` registers a binding. `Route.bind("post", lambda val: Post.query().where("slug", val).first())` registers a custom resolver.

**Key override**: `Route.model("post", Post, key="slug")` resolves by slug instead of id.

**Where constraints**: `Route.get("/posts/{id}", ...).where("id", "[0-9]+")` constrains the parameter pattern.

### Route Caching

In production, routes are compiled into a single dispatch table (regex → route) at boot time and cached. This avoids iterating all routes on every request.

### API vs Web Routes

| Feature | Web Routes | API Routes |
|---|---|---|
| Middleware group | `web` (session, CSRF) | `api` (throttle, stateless) |
| Prefix | none | `/api/v1` (configurable) |
| CSRF protection | Yes | No |
| Session | Yes | No |
| Response format | HTML (views) | JSON (resources) |

---

## 7. ORM Design (Codepyquent)

### Design Philosophy

Codepyquent is an active-record ORM that issues SQL through the driver directly and connection management. It provides Codepyquent's developer experience — chainable query builder, relationship methods, casts, accessors/mutators, scopes — while delegating to SQLAlchemy for database abstraction.

### PostgreSQL as Native Database

PostgreSQL is the default and primary database. Features leveraged:

| PostgreSQL Feature | ORM Support |
|---|---|
| `JSONB` columns | `casts = {"metadata": "json"}` — automatic jsonb serialization |
| `UUID` columns with `gen_random_uuid()` | `uuid("id")` in schema builder; auto-generation on insert |
| Full-text search (`tsvector`) | `Model.query().where_fulltext("body", "search term")` |
| Advisory locks | `DB.advisory_lock(key)` / `DB.advisory_unlock(key)` |
| Array columns | `casts = {"tags": "array"}` — PostgreSQL array type |
| `RETURNING` clause | Used for INSERT...RETURNING id (replaces `last_insert_rowid`) |
| Partial indexes | Schema builder supports `where` on index definitions |
| Enum types | Schema builder creates PostgreSQL `CREATE TYPE` enums |
| `EXCLUDE` constraints | Schema builder supports exclusion constraints |

### Connection Management

- **Async path (HTTP requests)**: Uses `asyncpg` via SQLAlchemy 2.0 async engine. Each request gets a scoped session from the connection pool. The session is committed/rolled-back at the end of the request lifecycle.
- **Sync path (CLI, migrations)**: Uses `psycopg` (psycopg3) via SQLAlchemy 2.0 sync engine. Migrations and seeders run synchronously.

### Model Architecture

```
┌─────────────────────────────────────────┐
│           ModelMeta (metaclass)          │
│  • Auto-resolves table_name from class   │
│  • Registers model in registry           │
│  • Boots traits (SoftDeletes, etc.)      │
└────────────────┬────────────────────────┘
                 │ inherits
                 ▼
┌─────────────────────────────────────────┐
│              Model (base)                │
│                                         │
│  Class methods:                         │
│    query() → QueryBuilder               │
│    find(id), findOrFail(id)              │
│    create(attrs), update_or_create(...)  │
│    where(col, val), where_in(col, vals)  │
│    with_(*relations)  # eager load       │
│    paginate(per_page, page)              │
│                                         │
│  Instance methods:                       │
│    save(), delete(), refresh()           │
│    update_attributes(attrs)              │
│    to_dict(), to_json()                  │
│    has_one/has_many/belongs_to/...        │
│                                         │
│  Configuration:                          │
│    fillable, hidden, visible, casts      │
│    timestamps, primary_key               │
│    __table__ (override)                  │
└─────────────────────────────────────────┘
```

### Query Builder

The query builder is chainable and lazy — SQL is only executed when a terminal method (`get()`, `first()`, `count()`, `paginate()`, `exists()`) is called.

**Chainable methods**: `where`, `or_where`, `where_in`, `where_not_in`, `where_null`, `where_not_null`, `where_between`, `where_like`, `where_has`, `where_doesnt_have`, `order_by`, `order_by_desc`, `latest`, `oldest`, `limit`, `offset`, `with_` (eager load), `with_trashed`, `only_trashed`, `scope`.

**Terminal methods**: `get()` → Collection, `first()` → Model|None, `firstOrFail()` → Model, `find(id)` → Model|None, `findOrFail(id)` → Model, `count()` → int, `exists()` → bool, `paginate(per_page, page)` → dict, `pluck(column)` → Collection, `update(data)` → int, `delete()` → int, `insert(data)` → int, `to_sql()` → str, `cursor()` → generator, `chunk(n, callback)`.

### Relationships

| Relationship | Method | Example |
|---|---|---|
| One-to-one | `has_one(Related)` | User has_one Profile |
| One-to-many | `has_many(Related)` | User has_many Post |
| Belongs-to | `belongs_to(Related)` | Post belongs_to User |
| Many-to-many | `belongs_to_many(Related, table, ...)` | User belongs_to_many Role |
| Has-one-through | `has_one_through(Related, Through)` | User has_one_through Car (via Mechanic) |
| Has-many-through | `has_many_through(Related, Through)` | User has_many_through Post (via Country) |
| Polymorphic one | `morph_one(Related, name)` | Image morph_one Commentable |
| Polymorphic many | `morph_many(Related, name)` | Post morph_many Comment |
| Polymorphic inverse | `morph_to(name)` | Comment morph_to Commentable |

**Eager loading**: `Post.query().with_("user", "comments").get()` loads all related models in 2 queries (1 for posts + 1 per relation), avoiding N+1.

**Lazy loading**: Accessing `post.user()` on a non-eager-loaded model triggers a single query.

### Collections

Query results are wrapped in a `Collection` class with chainable helpers: `map`, `filter`, `reject`, `each`, `pluck`, `contains`, `sort_by`, `group_by`, `first_where`, `where`, `first`, `last`, `count`, `is_empty`, `to_dict`, `to_json`, `paginate_meta`.

### Scopes

**Local scopes**: Defined as methods prefixed with `scope_` on the model:

```python
class Post(Model):
    def scope_published(self, query):
        return query.where("published", True)

# Usage: Post.query().scope("published").get()
```

**Global scopes**: Registered at boot time, applied automatically to every query. Soft deletes uses a global scope to exclude `deleted_at IS NOT NULL` records.

### Transactions

```python
DB.transaction(lambda:
    user = User.create({...})
    Post.create({"user_id": user.id, ...})
)
```

On exception, the transaction rolls back. Nested transactions use savepoints.

---

## 8. Migration System

### Schema Builder

The schema builder provides a fluent DSL for defining table structures. It generates PostgreSQL DDL and executes it via the database connection.

**Column types**:

| Method | PostgreSQL Type |
|---|---|
| `id()` | `BIGSERIAL PRIMARY KEY` (or `UUID PRIMARY KEY DEFAULT gen_random_uuid()`) |
| `string(name, length)` | `VARCHAR(length)` |
| `text(name)` | `TEXT` |
| `integer(name)` | `INTEGER` |
| `bigint(name)` | `BIGINT` |
| `boolean(name)` | `BOOLEAN` |
| `json(name)` / `jsonb(name)` | `JSON` / `JSONB` |
| `uuid(name)` | `UUID DEFAULT gen_random_uuid()` |
| `datetime(name)` | `TIMESTAMP` |
| `date(name)` | `DATE` |
| `time(name)` | `TIME` |
| `float(name)` | `REAL` |
| `decimal(name, p, s)` | `DECIMAL(p, s)` |
| `binary(name)` | `BYTEA` |
| `enum(name, values)` | Creates `CREATE TYPE` + column with CHECK |
| `foreign_id(name)` | `BIGINT` (for FK) |
| `morphs(name)` | `{name}_type VARCHAR` + `{name}_id BIGINT` |

**Column modifiers**: `nullable()`, `default(value)`, `unique()`, `index()`, `constrained(table, column)`, `cascade_on_delete()`, `restrict_on_delete()`, `null_on_delete()`.

**Table modifiers**: `timestamps()` (created_at, updated_at), `soft_deletes()` (deleted_at), `remember_token()`.

**Operations**: `Schema.create_table(name, callback)`, `Schema.table(name, callback)` (alter), `Schema.drop_table(name)`, `Schema.rename_table(from, to)`, `Schema.has_table(name)`, `Schema.has_column(table, column)`.

### Migration Files

Each migration file lives in `database/migrations/` with a timestamped name: `YYYY_MM_DD_HHMMSS_description_in_snake_case.py`.

Each file defines `up()` and `down()` functions (or a `Migration` subclass with `up()` and `down()` methods).

### Migrator

The migrator tracks applied migrations in a `migrations` table:

| Column | Type | Description |
|---|---|---|
| id | BIGSERIAL | Primary key |
| migration | VARCHAR(255) | Migration filename (without extension) |
| batch | INTEGER | Batch number (all migrations in one `migrate` run share a batch) |

**Operations**:
- `migrate` — Run all pending migrations in the current batch
- `migrate:rollback [--step=N]` — Roll back the last batch (or N steps)
- `migrate:refresh` — Roll back all, then re-migrate
- `migrate:fresh [--seed]` — Drop all tables, re-migrate, optionally seed
- `migrate:status` — Show ran/pending for each migration
- `migrate:install` — Create the migrations table
- `migrate:reset` — Roll back all migrations

### PostgreSQL-Specific Migration Features

- **Enum type management**: `Schema.create_enum_type("status", ["draft", "published", "archived"])` creates a PostgreSQL enum type. Migrations track and drop these on rollback.
- **Index with expression**: `Schema.table("posts", lambda t: t.index("lower(title)", name="posts_title_lower_idx"))` creates a functional index.
- **Partial index**: `t.index("published", where="published = true")` creates a partial index.
- **Full-text search index**: `Schema.table("posts", lambda t: t.gin_index("tsvector_column"))` creates a GIN index for full-text search.
- **Extensions**: `Schema.create_extension("pgcrypto")` enables PostgreSQL extensions.

---

## 9. Validation Layer

### Design

The validation layer follows a conventional `Validator` with a rule DSL. It operates on plain dicts (request input) and returns validated data or raises `ValidationException` with field-level error messages.

### Rule Syntax

Rules are specified as a dict mapping field names to rule lists:

```python
rules = {
    "title": ["required", "string", "max:255"],
    "body": ["required", "string", "min:10"],
    "email": ["required", "email", "unique:users,email"],
    "tags": ["array", "max:5"],
    "tags.*": ["string", "max:50"],
    "published": ["nullable", "boolean"],
}
```

### Built-in Rules

| Rule | Description |
|---|---|
| `required` | Field must be present and non-empty |
| `nullable` | Allows null/None values (skip other rules if null) |
| `sometimes` | Only validate if field is present |
| `string`, `integer`, `numeric`, `boolean`, `array`, `json` | Type checks |
| `email`, `url`, `uuid` | Format checks |
| `max:N`, `min:N`, `between:N,M`, `size:N` | Size constraints |
| `in:a,b,c`, `not_in:a,b,c` | Enumerated values |
| `unique:table,column,ignoreId` | Database uniqueness check |
| `exists:table,column` | Database existence check |
| `date`, `after:date`, `before:date` | Date validation |
| `regex:pattern` | Regular expression match |
| `confirmed` | Must match `{field}_confirmation` |
| `distinct` | Array values must be unique |
| `image`, `file`, `mimes:jpg,png` | File upload validation |

### Custom Rules

Custom rules are defined as callables:

```python
def uppercase_only(value):
    return value == value.upper()

rules = {"code": ["required", "string", uppercase_only]}
```

### Conditional Rules

Rules can be conditional via `Rule.when(condition, rules, default_rules)`:

```python
rules = {
    "company_name": Rule.when(lambda d: d.get("type") == "company", ["required", "string"]),
}
```

### FormRequest

FormRequest classes encapsulate validation and authorization:

**Lifecycle**:
1. Framework detects FormRequest type hint on controller method
2. Constructs FormRequest with the current HTTP request
3. Calls `authorize()` — if false, raises `AuthorizationException` (403)
4. Calls `validate()` — if rules fail, raises `ValidationException` (422)
5. Passes `validated()` dict to the controller method

**Error response**: On validation failure, the framework returns a 422 JSON response:
```json
{
    "message": "The given data was invalid.",
    "errors": {
        "title": ["The title is required."],
        "body": ["The body must be at least 10 characters."]
    }
}
```

### Custom Error Messages

Each FormRequest can define a `messages()` method returning field-rule → message mappings with `{field}` placeholder substitution.

---

## 10. Authentication & Authorization

### Guards

Guards are the authentication mechanism. Each guard has a driver and a user provider.

**Default guards**:

| Guard | Driver | Provider | Use Case |
|---|---|---|---|
| `web` | session | users (Codepyquent) | Browser sessions, HTML routes |
| `api` | token | users (Codepyquent) | API tokens, JSON routes |

**Session guard flow**:
1. Check session for `auth_id` → if present, load user from provider
2. On `attempt(credentials)`: look up user by identifier (email), verify password hash, store `auth_id` in session
3. On `logout()`: remove `auth_id` from session

**Token guard flow**:
1. Extract bearer token from `Authorization` header
2. Look up user by `api_token` column
3. Return user or None

**Custom guards**: Developers can define custom guards by implementing the `Guard` interface and registering in `config/auth.py`.

### User Providers

Providers retrieve users from a data source:

| Provider | Source |
|---|---|
| `codepyquent` | Codepyquent model (configured in `config/auth.py` as `providers.users.model`) |
| `database` | Raw DB table query (no model) |

### Gates

Gates are closure-based authorization checks:

```python
Gate.define("is-admin", lambda user: user is not None and user.is_admin)
Gate.define("update-post", lambda user, post: user.id == post.user_id)

# Usage:
if Gate.allows("update-post", user, post):
    ...
```

**Before callbacks**: `Gate.before(lambda user, ability: ...)` runs before all checks. Returning `True` short-circuits.

### Policies

Policies are class-based authorization organized around a model:

```python
class PostPolicy:
    def view_any(self, user): return True
    def view(self, user, post): return True
    def create(self, user): return user is not None
    def update(self, user, post): return user.id == post.user_id
    def delete(self, user, post): return user.id == post.user_id or user.is_admin
```

**Registration**: `Gate.policy(Post, PostPolicy)` in `AuthServiceProvider.boot()`.

**Usage in controller**: `self.authorize("update", user, post)` or via `@can` Forge directive in views.

**Policy methods**: `view_any`, `view`, `create`, `update`, `delete`, `restore`, `force_delete`. Plus any custom methods.

### Middleware

| Middleware | Behavior |
|---|---|
| `Authenticate` | Redirects to login (web) or returns 401 (api) if not authenticated |
| `Authorize(ability, model)` | Checks gate/policy; returns 403 if denied |
| `RedirectIfAuthenticated` | Redirects authenticated users away from login/register |
| `EnsureEmailIsVerified` | Blocks access until email is verified |

---

## 11. Events, Listeners, Jobs & Queues

### Event Dispatcher

The event dispatcher maintains a registry of event classes → listener lists. When `Event.dispatch(event)` is called, each registered listener is invoked.

**Registration** (in `EventServiceProvider.boot()`):

```python
Event.listen(PostPublished, [NotifySubscribers, SendTweet, UpdateFeed])
Event.listen("*", [LogAllEvents])  # Wildcard listener
```

**Dispatch**:

```python
Event.dispatch(PostPublished(post))
```

**Listener execution**: Listeners can be synchronous or queued:
- If a listener class implements `ShouldQueue`, it's pushed to the queue instead of executed inline
- Queued listeners are serialized and executed by a queue worker

**Subscriber pattern**: A class can implement `subscribe(dispatcher)` method that registers multiple listeners at once.

### Jobs

Jobs are units of work that can be dispatched to a queue:

```python
class ProcessPodcast(Job, ShouldQueue):
    queue = "default"
    timeout = 120
    tries = 3
    backoff = [5, 10, 30]  # retry delays in seconds

    def __init__(self, podcast_id):
        self.podcast_id = podcast_id

    def handle(self):
        # Process the podcast...
        pass
```

**Dispatching**: `Queue.push(ProcessPodcast(podcast_id))` or `ProcessPodcast(podcast_id).dispatch()`.

**Job lifecycle**:
1. Job is serialized (pickled) with its arguments
2. Pushed to the configured queue backend
3. Queue worker pops the job, deserializes it, calls `handle()`
4. On exception: retried up to `tries` times with `backoff` delay
5. After max retries: moved to `failed_jobs` table for manual retry

### Queue Backends

| Driver | Description |
|---|---|
| `sync` | Execute immediately (default for tests/dev) |
| `database` | Store in `jobs` table; worker polls |
| `redis` | Push to Redis list; worker pops via BLPOP |

**Queue worker** (`queue:work` command):
- Long-running process that polls the queue
- Supports `--queue=name`, `--timeout=N`, `--tries=N`, `--delay=N`
- Graceful shutdown on SIGTERM (finishes current job, then exits)
- Failed jobs stored in `failed_jobs` table with exception details

**Failed job handling**: `queue:failed` lists failed jobs. `queue:retry {id}` retries a specific job. `queue:retry all` retries all.

### Database Schema for Queues

**`jobs` table**:

| Column | Type | Description |
|---|---|---|
| id | BIGSERIAL | Primary key |
| queue | VARCHAR(255) | Queue name |
| payload | JSONB | Serialized job (pickle base64) |
| attempts | INTEGER | Number of attempts |
| reserved_at | TIMESTAMP | When reserved by a worker |
| available_at | TIMESTAMP | When the job becomes available |
| created_at | TIMESTAMP | Creation time |

**`failed_jobs` table**:

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| queue | VARCHAR(255) | Queue name |
| payload | JSONB | Serialized job |
| exception | TEXT | Exception traceback |
| failed_at | TIMESTAMP | Failure time |

---

## 12. Task Scheduling System

### Design

The scheduler provides a cron-like declaration syntax for recurring tasks. Tasks are registered in `routes/console.py` or `app/Console/Commands/` and executed by a single `schedule:run` command invoked via system cron.

### Schedule Declaration

```python
# routes/console.py
from codepy.facades import Schedule

Schedule.command("emails:send").hourly()
Schedule.command("reports:daily").daily_at("02:00")
Schedule.job(ProcessPodcast(podcast_id)).every_fifteen_minutes()
Schedule.call(lambda: cleanup_temp_files()).daily()
Schedule.command("telescope:prune").weekly()->sundays()->at("03:00")
```

### Frequency Methods

| Method | Cron Equivalent |
|---|---|
| `every_minute()` | `* * * * *` |
| `every_five_minutes()` | `*/5 * * * *` |
| `every_ten_minutes()` | `*/10 * * * *` |
| `every_fifteen_minutes()` | `*/15 * * * *` |
| `every_thirty_minutes()` | `*/30 * * * *` |
| `hourly()` | `0 * * * *` |
| `hourly_at(minute)` | `m * * * *` |
| `daily()` | `0 0 * * *` |
| `daily_at(time)` | `0 H:M * * *` |
| `weekly()` | `0 0 * * 0` |
| `monthly()` | `0 0 1 * *` |
| `quarterly()` | `0 0 1 1,4,7,10` |
| `yearly()` | `0 0 1 1 *` |
| `weekdays()` / `weekends()` | Day constraints |
| `mondays()` ... `sundays()` | Specific day |
| `between(start, end)` | Time window constraint |
| `when(callback)` | Truth-test constraint |

### Execution Model

A single cron entry runs the scheduler every minute:

```
* * * * * cd /app && python craft.py schedule:run >> /dev/null 2>&1
```

`schedule:run` evaluates all scheduled tasks and dispatches those due in the current minute. Overlapping prevention is available via `->without_overlapping()` which uses an advisory lock to prevent concurrent execution.

### Schedule Maintenance

- `->on_one_server()` — Use a lock to ensure the task runs on only one worker in a multi-instance setup
- `->run_in_background()` — Dispatch as an async background task
- `->then(callback)` — Chained callback after completion
- `->email_output_on_failure(email)` — Email the output if the task fails

---

## 13. CLI Tool Design

### Overview

The CLI is a Typer-based application invoked via `python craft.py <command>`. It provides scaffolding, database management, server control, and utility commands.

### Command Categories

#### Scaffolding (`make:*`)

| Command | Output |
|---|---|
| `make:model <Name> [-m] [-f]` | `app/Models/Name.py` + optional migration + factory |
| `make:controller <Name> [--resource] [--api]` | `app/Http/Controllers/Name.py` |
| `make:migration <name>` | `database/migrations/timestamp_name.py` |
| `make:middleware <Name>` | `app/Http/Middleware/Name.py` |
| `make:request <Name>` | `app/Http/Requests/Name.py` |
| `make:resource <Name> [--collection]` | `app/Http/Resources/Name.py` |
| `make:provider <Name>` | `app/Providers/Name.py` |
| `make:policy <Name> [--model=Model]` | `app/Policies/Name.py` |
| `make:event <Name>` | `app/Events/Name.py` |
| `make:listener <Name> [--event=Event]` | `app/Listeners/Name.py` |
| `make:job <Name>` | `app/Jobs/Name.py` |
| `make:command <Name>` | `app/Console/Commands/Name.py` |
| `make:seeder <Name>` | `database/seeders/Name.py` |
| `make:factory <Name>` | `database/factories/NameFactory.py` |
| `make:mail <Name>` | `app/Mail/Name.py` |
| `make:notification <Name>` | `app/Notifications/Name.py` |
| `make:channel <Name>` | `app/Broadcasting/Name.py` |

#### Database

| Command | Description |
|---|---|
| `migrate` | Run pending migrations |
| `migrate:rollback [--step=N]` | Roll back last batch |
| `migrate:refresh` | Roll back all + re-migrate |
| `migrate:fresh [--seed]` | Drop all tables + re-migrate + seed |
| `migrate:status` | Show migration status |
| `migrate:install` | Create migrations table |
| `migrate:reset` | Roll back all |
| `db:seed [--class=Seeder]` | Run seeders |
| `db:wipe` | Drop all tables |
| `db:show` | Show database info |
| `db:table <name>` | Show table structure |

#### Server

| Command | Description |
|---|---|
| `serve [--host] [--port] [--reload]` | Start uvicorn dev server |
| `serve --workers=N` | Start production server with N workers |

#### Queue

| Command | Description |
|---|---|
| `queue:work [--queue=name] [--tries=N] [--timeout=N]` | Start queue worker |
| `queue:restart` | Restart all workers gracefully |
| `queue:failed` | List failed jobs |
| `queue:retry {id\|all}` | Retry failed job(s) |
| `queue:flush` | Delete all failed jobs |

#### Schedule

| Command | Description |
|---|---|
| `schedule:run` | Run scheduled tasks due now |
| `schedule:list` | List all scheduled tasks |
| `schedule:work` | Run scheduler in foreground (no cron needed) |

#### Utility

| Command | Description |
|---|---|
| `key:generate` | Generate APP_KEY into .env |
| `route:list` | List all registered routes |
| `route:cache` | Cache route definitions |
| `route:clear` | Clear route cache |
| `config:cache` | Cache configuration |
| `config:clear` | Clear config cache |
| `tinker` | Interactive REPL with app context |
| `test` | Run pytest |
| `optimize` | Cache config + routes |
| `clear-compiled` | Clear all caches |
| `package:discover` | Discover installed packages |
| `stub:publish` | Publish customizable stubs |

### Custom Commands

Custom commands live in `app/Console/Commands/` and extend `codepy.cli.Command`. They define a `signature` (command name + arguments) and a `handle()` method. They are auto-discovered by the CLI application.

### Command Registration

Commands are auto-discovered from `app/Console/Commands/`. Alternatively, they can be registered in a `CommandServiceProvider`:

```python
class CommandServiceProvider(ServiceProvider):
    def commands(self):
        return [SendEmailsCommand, GenerateSitemapCommand]
```

---

## 14. Configuration System

### Design

Configuration is stored as Python modules in `config/`. Each file exposes module-level variables. The `Config` repository loads all files at boot, merges with environment variables, and provides dot-notation access.

### Loading Process

```
1. Application.register_config()
2. Config repository scans config/ directory
3. For each *.py file (excluding __init__.py):
   a. Import the module
   b. Extract all non-private, non-callable attributes
   c. Store under the filename key (e.g., config/app.py → "app")
4. Environment variables override config values via env() helper
```

### Environment Loading

Each config file uses the `env(key, default)` helper to read environment variables:

```python
# config/app.py
from codepy.config import env

APP_NAME = env("APP_NAME", "Codepy")
APP_ENV = env("APP_ENV", "local")
APP_DEBUG = env("APP_DEBUG", True)  # String "true" → boolean True
APP_KEY = env("APP_KEY", "")
APP_URL = env("APP_URL", "http://localhost:8000")
```

### Access

```python
# Via facade
Config.get("app.debug")           # → True
Config.get("database.default")     # → "pgsql"
Config.set("app.timezone", "UTC")
Config.has("app.key")              # → True

# Via helper
from codepy.support import config
config("app.debug")                 # → True
```

### Configuration Caching

In production, `config:cache` compiles all config files + env overrides into a single cached dict, loaded directly without scanning. `config:clear` removes the cache.

### Environment-Specific Config

The `APP_ENV` variable determines which `.env` file to load:
- `.env` (default)
- `.env.local` (local development overrides)
- `.env.testing` (test suite)
- `.env.production` (production)

Values in more specific files override the base `.env`.

---

## 15. Exception Handling Architecture

### Design

All exceptions flow through a central `Handler`. The handler has two responsibilities:

1. **report(exception)** — Log or send to monitoring (Sentry, Bugsnag, etc.)
2. **render(request, exception)** — Convert to an HTTP response

### Exception Hierarchy

```
CodepyException (base)
├── HttpException
│   ├── NotFoundHttpException (404)
│   ├── MethodNotAllowedHttpException (405)
│   ├── ThrottleRequestsException (429)
│   └── HttpResponseException (custom status)
├── ModelNotFoundException (404)
├── AuthorizationException (403)
├── AuthenticationException (401)
├── ValidationException (422)
│   └── errors: dict[str, list[str]]
├── TokenMismatchException (419)
├── MaintenanceModeException (503)
└── MassAssignmentException (500)
```

### Handler Design

```python
class Handler:
    def render(self, request, exception) -> Response:
        # Convert exception to HTTP response
        # JSON for API requests, HTML for web requests
        pass

    def report(self, exception):
        # Log exception, send to Sentry, etc.
        pass

    def should_report(self, exception) -> bool:
        # Check against $dont_report list
        pass
```

### Don't Report List

Some exceptions are expected and should not be logged:

```python
class Handler:
    _dont_report = [
        HttpException,
        NotFoundHttpException,
        ValidationException,
        AuthenticationException,
    ]
```

### Custom Exception Handler

The application can override the framework handler by creating `app/Exceptions/Handler.py`:

```python
class Handler(BaseHandler):
    def render(self, request, exception):
        if request.expects_json():
            return JsonResponse({"message": exception.message}, exception.status_code)
        return self.view("errors.500", {"exception": exception})
```

### Render Behavior

| Exception | API (JSON) | Web (HTML) |
|---|---|---|
| ValidationException | 422 + errors dict | Redirect back with errors + old input |
| AuthenticationException | 401 JSON | Redirect to login |
| AuthorizationException | 403 JSON | 403 error page |
| ModelNotFoundException | 404 JSON | 404 error page |
| HttpException | {status} JSON | Error template by status code |
| Generic Exception | 500 JSON (debug: with traceback) | 500 error page (debug: with traceback) |

### Debug Mode

When `APP_DEBUG=True`:
- Full tracebacks are included in responses
- Detailed error pages show file, line, and code context
- No sensitive data is hidden

When `APP_DEBUG=False`:
- Generic "Server Error" messages
- No tracebacks in responses
- Errors logged but not exposed

---

## 16. Template Engine Integration

### Forge Engine

Forge is a Jinja2-based templating engine extended with Forge directives. It provides a two-phase compilation:

1. **Directive preprocessing**: Convert `@directives` to Jinja2 `{{ }}` / `{% %}` syntax
2. **Jinja2 rendering**: Standard Jinja2 template rendering with autoescape

### Forge Directives

| Directive | Compiles To | Description |
|---|---|---|
| `@extends('layouts.app')` | `{% extends "layouts.app" %}` | Layout inheritance |
| `@section('name') ... @endsection` | `{% block name %} ... {% endblock %}` | Define a block |
| `@yield('name')` | `{% block name %}{% endblock %}` | Output a block |
| `@include('partials.nav')` | `{% include "partials.nav" %}` | Include a partial |
| `@if(cond)` / `@elseif` / `@else` / `@endif` | `{% if %}` / `{% elif %}` / `{% else %}` / `{% endif %}` | Conditionals |
| `@foreach(items as item)` / `@endforeach` | `{% for item in items %}` / `{% endfor %}` | Loops |
| `@for(i in range)` / `@endfor` | `{% for %}` / `{% endfor %}` | For loops |
| `@while(cond)` / `@endwhile` | `{% while %}` / `{% endwhile %}` | While loops |
| `@csrf` | Hidden CSRF input | CSRF token field |
| `@method('PUT')` | Hidden method override | HTTP method spoofing |
| `@auth` / `@endauth` | `{% if auth() %}` / `{% endif %}` | Authenticated block |
| `@guest` / `@endguest` | `{% if not auth() %}` / `{% endif %}` | Guest block |
| `@can('ability', model)` / `@endcan` | `{% if can('ability', model) %}` / `{% endif %}` | Authorization check |
| `@cannot('ability', model)` / `@endcannot` | `{% if not can(...) %}` / `{% endif %}` | Authorization deny |
| `@json(data)` | `{{ data \| tojson }}` | JSON encode |
| `@stack('scripts')` | Block placeholder | Stack output |
| `@push('scripts') ... @endpush` | Block push | Stack content |
| `@isset(var)` / `@endisset` | `{% if var is defined %}` / `{% endif %}` | Variable exists |
| `@empty(items)` / `@endempty` | `{% if not items %}` / `{% endif %}` | Empty check |
| `{{-- comment --}}` | `{# comment #}` | Comment |

### Global Template Variables

These are available in all templates:

| Variable | Source |
|---|---|
| `auth()` | `Auth.user()` — current authenticated user or None |
| `csrf_token()` | Session-based CSRF token |
| `config(key, default)` | `Config.get(key, default)` |
| `session(key, default)` | Session get |
| `route(name, **params)` | `Route.url_for(name, **params)` |
| `asset(path)` | Asset URL |
| `url(path)` | Full URL |
| `old(key, default)` | Old input from session |
| `errors` | Validation errors bag |
| `can(ability, model)` | Gate check |

### View Namespaces

Views are resolved from `resources/views/` by default. Packages can register additional namespaces:

```python
View.add_namespace("admin", "packages/admin/resources/views")
# Usage: self.view("admin::dashboard", {...})
```

### View Sharing

Variables can be shared globally with all views:

```python
View.share("sidebar_items", SidebarService.get_items())
```

### View Composers

View composers attach data to views automatically when they're rendered:

```python
View.composer("posts.*", PostViewComposer)
View.composer("layouts.app", lambda view: view.with("nav", NavService.get_items()))
```

---

## 17. Modular Package Structure

### Design Goal

The framework supports a modular package system where self-contained features can be developed, installed, and reused across applications — mirroring the framework's package ecosystem.

### Package Structure

A Codepy package is a Python package with a specific structure:

```
my_package/
├── __init__.py
├── ServiceProvider.py          # Package's service provider
├── routes/
│   └── web.py                  # Package routes
├── resources/
│   └── views/                  # Package views
├── database/
│   ├── migrations/             # Package migrations
│   └── seeders/                # Package seeders
├── config.py                   # Package config defaults
└── pyproject.toml              # Package metadata
```

### Package Discovery

When a package is installed (via pip), the framework's `package:discover` command scans installed packages for a `ServiceProvider` class. Discovered providers are registered automatically.

A package's `ServiceProvider` can:
- `register()` — Bind services into the container
- `boot()` — Register routes, views, migrations, policies
- `load_routes_from(path)` — Register package routes
- `load_views_from(path, namespace)` — Register view namespace
- `load_migrations_from(path)` — Register migration directory
- `merge_config_from(path, key)` — Merge package config
- `commands()` — Register CLI commands

### Module Discovery

Application code in `app/` is auto-discovered:
- Models in `app/Models/` are registered in the model registry
- Policies in `app/Policies/` are auto-loaded if registered in `AuthServiceProvider`
- Commands in `app/Console/Commands/` are auto-discovered by the CLI
- Events in `app/Events/` and Listeners in `app/Listeners/` are mapped in `EventServiceProvider`

---

## 18. Developer Experience Principles

### Expressive Syntax

Codepy prioritizes readability and expressiveness over brevity. Code should read like natural language:

| Principle | Example |
|---|---|
| Fluent chains | `Post.query().where("published", True).order_by_desc("created_at").paginate(15)` |
| Named routes | `redirect(route="posts.show", posts=post.id)` |
| Declarative validation | `rules = {"title": ["required", "string", "max:255"]}` |
| Resource routing | `Route.resource("posts", PostController)` |
| Facade accessors | `DB.table("users").where("active", True).get()` |
| Forge directives | `@foreach(posts as post) ... @endforeach` |
| Convention over configuration | `User` model → `users` table automatically |

### Convention Over Configuration

| Convention | Rule |
|---|---|
| Table name | CamelCase → snake_case → pluralized (`BlogPost` → `blog_posts`) |
| Foreign key | `{related_model_snake}_id` (`user_id`) |
| Primary key | `id` (override via `primary_key` class attr) |
| Timestamps | `created_at`, `updated_at` (auto-managed when `timestamps = True`) |
| Soft delete | `deleted_at` column |
| Fillable | Explicit allowlist for mass assignment |
| Hidden | Strip from JSON serialization |
| Migration naming | `YYYY_MM_DD_HHMMSS_create_{table}_table` |
| Route naming | `{resource}.{action}` (e.g., `posts.index`, `posts.show`) |

### Hot Reload

During development, `codepy serve` runs uvicorn with `--reload`, which watches for file changes and restarts the server automatically. The framework also supports:
- Template auto-recompilation (Forge checks file mtime)
- Config reload on change (in debug mode)
- Migration auto-run on server start (optional, via `--migrate` flag)

### Error Pages

In debug mode, exception pages show:
- The exact file and line number
- Surrounding code context (10 lines before/after)
- Request details (method, URL, headers, body, session)
- Stack trace with file links
- Query log (all SQL executed during the request)

### Testing

The framework provides test helpers:
- `TestClient` wrapper that boots the app and makes HTTP requests
- `ModelFactory` for generating test data
- `Faker` integration for realistic data
- `RefreshDatabase` trait that migrates fresh before each test
- `acting_as(user)` helper for authenticated requests

### REPL (Tinker)

`codepy tinker` launches an interactive Python REPL with the application context loaded. All facades, models, and container services are available for inspection and experimentation.

---

## 19. Additional Subsystems

### Broadcasting (WebSockets)

Real-time events broadcast to WebSocket channels:

**Channel types**:
- `PublicChannel` — Anyone can listen
- `PresenceChannel` — Authenticated members only; exposes who's online
- `PrivateChannel` — Authorized per-user

**Broadcasting flow**:
1. Event implements `ShouldBroadcast` interface
2. Event's `broadcast_on()` returns channel names
3. Event's `broadcast_with()` returns payload data
4. Dispatcher serializes event and pushes to WebSocket backend
5. Frontend client subscribes to channels and receives events

**Backends**: Redis Pub/Sub, Pusher, or native WebSocket server (via Starlette WebSocket).

### Filesystem

Multi-disk filesystem abstraction:

| Disk | Driver |
|---|---|
| `local` | Local filesystem (`storage/app/`) |
| `public` | Public local (`storage/app/public/` → symlinked to `/static/`) |
| `s3` | Amazon S3 |
| `gcs` | Google Cloud Storage |

**Operations**: `Storage.disk("s3").put("path", content)`, `.get(path)`, `.download(path)`, `.url(path)`, `.exists(path)`, `.delete(path)`, `.files(directory)`, `.all_files(directory)`.

### Mail

Mail manager with multiple drivers:

| Driver | Description |
|---|---|
| `smtp` | SMTP server |
| `ses` | Amazon SES |
| `postmark` | Postmark API |
| `log` | Write to log file (for testing) |

**Mailables**: Mail is sent via Mailable classes that define the subject, view, attachments, and recipients:

```python
class WelcomeEmail(Mailable):
    def envelope(self): return Envelope(subject="Welcome to Codepy")
    def content(self): return Content(view="emails.welcome", with_={"user": self.user})
    def attachments(self): return [Attachment.from_path("/path/to/file.pdf")]
```

### Notifications

Multi-channel notifications:

| Channel | Driver |
|---|---|
| `mail` | Email |
| `database` | Store in `notifications` table |
| `broadcast` | WebSocket push |
| `slack` | Slack webhook |
| `discord` | Discord webhook |

**Usage**: `user.notify(PostPublishedNotification(post))` sends via all channels enabled for the user's preferences.

### Hashing

Pluggable hash drivers:

| Driver | Algorithm |
|---|---|
| `bcrypt` (default) | bcrypt with cost factor 12 |
| `argon2` | Argon2id |

### Encryption

Symmetric encryption service using `APP_KEY`:

- `encrypter.encrypt(plaintext)` → base64 ciphertext
- `encrypter.decrypt(ciphertext)` → plaintext
- Uses AES-256-GCM with PBKDF2 key derivation

### Localization

Language files in `resources/lang/{locale}/`:

```python
# resources/lang/en/messages.py
welcome = "Welcome, :name!"
post_count = "{0} post | {0} posts"
```

**Usage**: `Lang.get("messages.welcome", name="Jane")`, `Lang.choice("messages.post_count", 5)`.

Locale is set via `APP_LOCALE` config and can be switched per-request.

### Logging

Multi-channel logging with stacks:

| Channel | Driver | Description |
|---|---|---|
| `single` | file | Single log file |
| `daily` | file | Rotated daily, kept N days |
| `stderr` | stream | Standard error |
| `syslog` | syslog | System log |
| `slack` | webhook | Slack channel |

**Stacks**: A stack combines multiple channels. The default stack writes to `single` and `stderr`:

```python
# config/logging.py
default = "stack"
stacks = {
    "stack": {
        "driver": "stack",
        "channels": ["single", "stderr"],
    }
}
```

### Database Transactions

```python
DB.transaction(lambda:
    user = User.create({...})
    Account.create({"user_id": user.id, ...})
)
```

- Nested transactions use PostgreSQL savepoints
- On exception, the outermost transaction rolls back
- `DB.begin_transaction()`, `DB.commit()`, `DB.rollback()` for manual control

### Query Logging

In debug mode, every SQL query is logged with:
- The SQL string with bound parameters
- Execution time in milliseconds
- The calling file and line (via stack inspection)
- Connection name

This feeds the debug error page's query log panel.

### Configuration Publishing

Packages can publish their config, views, migrations, and assets to the application:

```python
self.publishes({
    "config/package.py": config_path("package.py"),
    "resources/views/": resource_path("views/vendor/package/"),
}, group="package-assets")
```

`vendor:publish --provider=PackageServiceProvider --tag=package-assets` copies files.

### HTTP Client

A Guzzle-like HTTP client for making outgoing requests:

```python
response = Http.with_headers({"Authorization": f"Bearer {token}"}) \
    .post("https://api.example.com/webhook", json=payload)

response.ok()        # → True/False
response.json()      # → dict
response.status()     # → 200
response.body()      # → str
```

### Rate Limiting

Configurable rate limiter for the `throttle` middleware:

```python
# In RouteServiceProvider
RateLimiter.for("api", lambda request: Limit.per_minute(60))
RateLimiter.for("uploads", lambda request: Limit.per_minute(10).by(request.user.id))
```

### Horizon (Queue Dashboard)

Optional queue monitoring dashboard showing:
- Job throughput and wait times
- Failed jobs with retry capability
- Queue worker status
- Recent jobs with payload and exception details

---

## Appendix: Dependency Map

| Package | Purpose | Version |
|---|---|---|
| `fastapi` | ASGI framework | >=0.104 |
| `starlette` | ASGI toolkit (underlying FastAPI) | >=0.27 |
| `uvicorn[standard]` | ASGI server | >=0.24 |
| `sqlalchemy[asyncio]` | Database abstraction | >=2.0 |
| `asyncpg` | Async PostgreSQL driver | >=0.29 |
| `psycopg[binary]` | Sync PostgreSQL driver (CLI/migrations) | >=3.1 |
| `pydantic` | Data validation / settings | >=2.0 |
| `jinja2` | Template engine | >=3.1 |
| `typer` | CLI framework | >=0.9 |
| `python-multipart` | Form parsing | >=0.0.6 |
| `bcrypt` | Password hashing | >=4.0 |
| `faker` | Test data generation | >=20.0 |
| `httpx` | HTTP client / testing | >=0.25 |
| `pytest` | Testing framework | >=7.4 |
| `redis` | Redis client (queue/cache) | >=5.0 (optional) |
| `boto3` | AWS SDK (S3/SES) | >=1.34 (optional) |

---

## Appendix: PostgreSQL Connection Schema

```
                    ┌─────────────────────────────────┐
                    │        Application              │
                    │   (Service Container)           │
                    └──────────┬──────────────────────┘
                               │
                    ┌──────────▼──────────────────────┐
                    │     DatabaseManager (singleton) │
                    │   ┌──────────┐  ┌──────────┐     │
                    │   │Async     │  │Sync      │     │
                    │   │Engine    │  │Engine    │     │
                    │   │(asyncpg) │  │(psycopg)  │     │
                    │   └────┬─────┘  └────┬─────┘     │
                    └────────┼─────────────┼──────────┘
                             │            │
                             │            │
                    ┌────────▼────────────▼──────────┐
                    │      PostgreSQL 16+             │
                    │   ┌──────────────────────┐     │
                    │   │  Connection Pool     │     │
                    │   │  (max_connections=20)│     │
                    │   └──────────────────────┘     │
                    │                               │
                    │   Databases:                  │
                    │   • application data          │
                    │   • jobs queue table          │
                    │   • failed_jobs table         │
                    │   • sessions (db driver)      │
                    │   • cache (db driver)          │
                    └───────────────────────────────┘
```

### Default `config/database.py`

| Key | Default | Description |
|---|---|---|
| `default` | `"pgsql"` | Default connection |
| `connections.pgsql.driver` | `"postgresql"` | PostgreSQL driver |
| `connections.pgsql.host` | `env("DB_HOST", "127.0.0.1")` | Host |
| `connections.pgsql.port` | `env("DB_PORT", 5432)` | Port |
| `connections.pgsql.database` | `env("DB_DATABASE", "forge")` | Database name |
| `connections.pgsql.username` | `env("DB_USERNAME", "forge")` | Username |
| `connections.pgsql.password` | `env("DB_PASSWORD", "")` | Password |
| `connections.pgsql.sslmode` | `env("DB_SSLMODE", "prefer")` | SSL mode |
| `connections.pgsql.pool_size` | `env("DB_POOL_SIZE", 20)` | Pool size |
| `connections.pgsql.max_overflow` | `env("DB_MAX_OVERFLOW", 10)` | Max overflow |
| `connections.pgsql.pool_recycle` | `3600` | Connection recycle (seconds) |
| `connections.sqlite.driver` | `"sqlite"` | SQLite (for tests only) |

---

*End of Design Document*
