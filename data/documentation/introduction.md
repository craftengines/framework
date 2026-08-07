# Introduction to Craft

Craft is a modern, full-stack MVC backend framework that brings expressive conventions, developer ergonomics, and batteries-included design to the Python ecosystem. Built on top of **Starlette** (the ASGI HTTP layer), its own multi-driver database layer and **Craft ORM** (SQLite, PostgreSQL, and MySQL with the same SQL), and **Jinja2** (preprocessed as the **Forge** engine), Craft makes it easy to construct robust APIs and server-rendered web applications.

---

## Core Philosophy

1. **Convention over Configuration**: files go in specific directories, classes adhere to consistent name patterns, and dependencies resolve automatically.
2. **Developer Ergonomics**: Powerful command-line tooling, dynamic facades, and automatic dependency injection minimize boilerplate.
3. **High Performance**: Async controller actions are awaited natively, and dependencies boot lazily.

---

## Directory Structure

An out-of-the-box Craft project follows this standard layout:

```
project/
├── app/                        # Application Code
│   ├── Http/
│   │   ├── Controllers/        # Request handlers (Actions)
│   │   ├── Middleware/         # HTTP request/response middleware
│   │   ├── Requests/           # Typed validation requests (FormRequest)
│   │   └── Resources/          # API JSON transformers
│   ├── Models/                  # ActiveRecord database entities (Craft ORM)
│   ├── Policies/                # Gate authorization policy classes
│   ├── Providers/               # Service Providers for DI binding
│   └── Services/               # Custom business logic layer
├── config/                      # Configuration Files (env merged)
├── database/                    # Migrations, Seeders, and Factories
├── resources/
│   └── views/                   # HTML templates (Forge)
├── routes/                      # Route maps (web.py, api.py, console.py)
├── storage/                     # File uploads, cache, logs
└── dev.py                    # CLI command runner
```

---

## Getting Started

### Prerequisites

- Python 3.11 or newer
- Docker & Docker Compose — optional, only for the PostgreSQL setup

### Installation & Run

The default database is SQLite, so no database server is needed:

1. Clone your project repository and install: `pip install -e ".[dev]"`.
2. Copy the environment file: `cp .env.example .env`.
3. Generate the key that signs session cookies: `python dev.py key:generate`.
4. Create and seed the schema: `python dev.py migrate --seed`.
5. Serve it: `python dev.py serve` — the app is at `http://127.0.0.1:8000`.

Or with Docker, which brings up the app and PostgreSQL together:

```bash
docker compose up -d --build
```

Access it at `http://localhost:8300`.
