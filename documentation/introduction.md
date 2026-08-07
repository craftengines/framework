# Introduction to Codepy

Codepy is a modern, full-stack MVC backend framework that brings the framework's expressive conventions, developer ergonomics, and batteries-included design to the Python ecosystem. Built on top of **FastAPI** (for high-performance routing), **SQLAlchemy 2.0 Core** (for database abstraction), and **Jinja2** (preprocessed as the **Forge** engine), Codepy makes it easy to construct robust APIs and server-rendered web applications.

---

## Core Philosophy

1. **Convention over Configuration**: files go in specific directories, classes adhere to consistent name patterns, and dependencies resolve automatically.
2. **Developer Ergonomics**: Powerful command-line tooling, dynamic facades, and automatic dependency injection minimize boilerplate.
3. **High Performance**: Native async/await support, fast connection pooling via pgsql (asyncpg), and lazy dependency booting.

---

## Directory Structure

An out-of-the-box Codepy project follows this standard layout:

```
project/
├── app/                        # Application Code
│   ├── Http/
│   │   ├── Controllers/        # Request handlers (Actions)
│   │   ├── Middleware/         # HTTP request/response middleware
│   │   ├── Requests/           # Typed validation requests (FormRequest)
│   │   └── Resources/          # API JSON transformers
│   ├── Models/                  # ActiveRecord database entities (Codepyquent)
│   ├── Policies/                # Gate authorization policy classes
│   ├── Providers/               # Service Providers for DI binding
│   └── Services/               # Custom business logic layer
├── config/                      # Configuration Files (env merged)
├── database/                    # Migrations, Seeders, and Factories
├── resources/
│   └── views/                   # HTML templates (Forge)
├── routes/                      # Route maps (web.py, api.py, console.py)
├── storage/                     # File uploads, cache, logs
└── craft.py                    # CLI command runner
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- Docker & Docker Compose (for PostgreSQL container)

### Installation & Run

1. Clone your project repository.
2. Configure your environment variables in `.env` (copied from `.env.example`).
3. Boot the Docker containers:
   ```bash
   docker compose up --build -d
   ```
4. Run migrations and seed the database inside the container:
   ```bash
   docker exec -it framework python craft.py migrate fresh
   docker exec -it framework python craft.py db seed
   ```
5. Access your application locally at `http://localhost:8300`.
