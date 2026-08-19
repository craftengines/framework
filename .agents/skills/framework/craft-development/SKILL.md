---
name: craft-framework-development
description: Framework-level guidelines and developer conventions for generating, refactoring, and maintaining the core components of the Craft framework.
---

# Craft Framework Development Guidelines (Framework Skill)

This skill governs modifications to the core framework packages under the `craft/` directory.

## Core Objective
Ensure that core libraries (container, ORM, router, queues, view engine, validation) remain abstract, high-performance, and free of application-specific business logic.

---

## 1. Subsystem Responsibilities

* **`craft.container`**: Manages class binding and dependency resolution. Scoped services must use `contextvars` to ensure thread-safety.
* **`craft.orm`**: Implements Active Record on a **custom query builder** over `sqlite3`/`psycopg2`/`PyMySQL` — no SQLAlchemy, no Pydantic. Supports native **Vector & Semantic Search** (`where_vector_similar`, `order_by_vector_similarity`, `similarity_score` calculation).
* **`craft.ai` (Facade `AI`)**: Unified AI SDK and Autonomous Agent Orchestrator. Supports Gemini, OpenAI, Claude, Ollama, and Mock drivers for chat, text generation, vector embeddings, and multi-turn function calling (`AI.agent(tools=[...])`).
* **`craft.agents` / `craft.mcp` (Facades `Agent`, `MCP`)**: Declarative `AgentTool` definitions with JSON Schema inference and strict RBAC authorization checks. Features a JSON-RPC 2.0 Model Context Protocol (`MCPServer`) for AI assistants and IDE integrations.
* **`craft.storage` (Facade `Storage`)**: Multi-disk object storage abstraction supporting `local`, `public`, and S3-compatible cloud disks (`s3` for AWS S3, MinIO, Cloudflare R2, Google Cloud Storage) with signed temporary URLs.
* **`craft.queue` (Facade `Queue`)**: Dispatches and runs queued tasks. Supported drivers: `sync`, `database`, `redis`. Payloads must be strictly serialized as **JSON**; never use `pickle`. Supports delayed jobs via Redis ZSETs and atomic pop claiming.
* **`craft.mail` (Facade `Mail`)**: Fluent email and notification delivery supporting `smtp` (TLS/SSL), `log`, and `array` transports. Supports `Mail.to().send()`, `Mail.raw()`, and declarative `Mailable` classes integrated with Forge templates.
* **`craft.media` (Facades `Image`, `Media`)**: Fluent image manipulation engine (Pillow-backed) supporting WebP/AVIF export, watermarking, filters, geometry transformations, video metadata extraction, and database-tracked media models.
* **`craft.view`**: Preprocesses Forge directive syntax into standard Jinja2 syntax and caches compiled templates.
* **`craft.security`**: WAF/IDS firewall, honeypot traps, brute-force throttling, login audit logs, Captcha, and Post-Quantum Cryptography (PQC) readiness.

---

## 2. Framework Guidelines

* **All code, orientation comments, and docstrings are 100% English — no exceptions, no partial translations left "for later."** This includes the `Category/Relations/References` headers, inline comments, commit messages, and every file under `data/` (application code, `documentation/*.md`, `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`). Files outside `data/` — this repo's own `.agents/` orchestration layer — are Portuguese by a separate, deliberate convention; that split does not extend to anything shipped as the framework or its docs.
  * **Any other human language enters the application only through the translation layer** (`resources/lang/catalog.json`, `database/seeders/TranslationSeeder.py`, the `__()` helper) — never hardcoded in a view, controller, or comment. A hardcoded non-English string in `data/` is either dead code to delete or a missing i18n key to add, not something to leave as-is.
  * Before adding a file under `data/`, and before finishing any change that touches one, check it doesn't reintroduce non-English text outside i18n: `Select-String -Pattern "[àáâãéêíóôõúçÀÁÂÃÉÊÍÓÔÕÚÇ]"` (or the Linux/macOS equivalent `grep -RP '[à-üÀ-Ü]'`) over the changed files, excluding `resources/lang/`, `TranslationSeeder.py`, and `documentation/localization.md`. A non-empty match is a defect, not a style nit — it directly degrades the next agent's ability to work in this codebase without guessing at meaning.
* Enforce strict type hints and docstrings on every public function and class.
* Do not import modules from the `app/` folder into the `craft/` framework package (avoid circular dependencies).
* New files under `engine/` (and edits to existing ones) carry the `Category/Relations/References` header docstring — see `engine/plugins/manager.py` for the shape.

---

## 3. Every change to the framework gets a CHANGELOG entry

**Non-negotiable, not just at release time.** The same change that fixes a
bug, adds a feature, bumps a dependency, or closes a vulnerability adds its
line to `## [Unreleased]` in `data/CHANGELOG.md`, in the same commit. This is
the mechanism that lets a developer or another agent understand what
happened to the framework without re-deriving it from a diff or `git log` —
and it is how they can help: a change nobody can see in the changelog is a
change nobody can review, build on, or flag a regression against.

Categories (Keep a Changelog): **Added**, **Changed**, **Fixed**,
**Security** (any vulnerability closed or hardening applied — state the
exposure, not just the patch), **Deprecated**, **Removed**. Full policy,
including how a release gets cut and why the release counter (`rNNNNN`)
always increments by exactly 1, is in `data/CONTRIBUTING.md` under
"Versioning and releases" — read it before your first change, not after.

---

## 4. Database-Driven Architecture: Zero Hardcoding

**All application state, security, internationalization, and feature toggles must be backed by the database.**

* **Translations (`translations` table)**:
  * Text displayed to users must be resolved dynamically via the translation engine (`__()`), which prioritizes database entries in `translations` with fallback to config.
  * Never hardcode UI labels, validation messages, or notifications.
* **Authorization (`roles`, `permissions`, `groups`, `group_role`, etc.)**:
  * Never hardcode access control logic like `if user.is_admin` or `if user.id == 1`.
  * Use Gate, policies, and database permissions.
* **Modules & Feature Toggles (`modules` table)**:
  * Features subject to activation/deactivation must query the `modules` table (`enabled=True/False`).
* **Dynamic Configuration (`settings` table)**:
  * System-wide parameters that administrators can adjust at runtime belong in the `settings` database table, keeping `.env` strictly for environment/driver infrastructure config.
