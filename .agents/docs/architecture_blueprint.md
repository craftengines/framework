# Craft Core Framework Architecture Blueprint

This document explains the structural flow and runtime conventions of the Craft framework.

---

## 1. Request Lifecycle

The HTTP request execution path proceeds as follows:

```
HTTP Request
    │
    ▼
┌──────────────────┐
│  ASGI Server     │  Uvicorn receives request, passes it to Starlette app.
│  (Uvicorn)       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  HTTP Kernel     │  Starts request scope container, wraps Starlette Request.
│                  │  Registers scoped bindings.
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Global          │  Runs global middlewares (CORS, StartSession, etc.).
│  Middleware      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Router          │  Matches routes to actions, extracts route parameters,
│  (Dispatch)      │  resolves middleware groups (web/api).
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Controller      │  Resolves action method dependencies via DI Container.
│  Action          │  Validates input if FormRequest is type-hinted.
│                  │  Renders and returns Response.
└──────────────────┘
```

---

## 2. Bootstrapping Flow

The application is bootstrapped from [bootstrap/app.py](file:///d:/data/www/craft/bootstrap/app.py):

1. **`create_app()`** instantiates the `Application` class.
2. **`register_config()`** scans the `config/` directory and registers configuration files in the `config` repository binding.
3. **`register_provider()`** registers all framework and application-level service providers, executing their `register()` methods to bind core services.
4. **Facade binding:** `Facade._app = app` wires dynamic facades to the active application context.
5. **`boot()`** invokes the `boot()` methods of all registered service providers to perform post-registration configurations (like loading route files).
6. **Kernel initialization:** The application kernel wraps the booted application instance into an ASGI starlette runtime.

---

## 3. Database Connection Mapping

Craft relies on two database connections depending on the context:

* **HTTP Requests (Async context):** Resolves connections using `asyncpg` via SQLAlchemy's AsyncEngine.
* **CLI commands, migrations, and seeders (Sync context):** Resolves connections synchronously using `psycopg3` via SQLAlchemy's standard Engine to guarantee linear script execution.
