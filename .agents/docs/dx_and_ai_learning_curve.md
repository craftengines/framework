# Developer Experience (DX) & AI Agent Learning Curve Analysis

This document records the architecture and Developer Experience goals of **Craft**, and outlines strategies to optimize the learning curve for both **human developers** and **AI agents**.

---

## 1. Architectural & DX Summary

Craft is convention-based (rigid directory layout mirrored after mature MVC
frameworks) rather than freeform. Boilerplate per feature is low: a model,
migration, controller, and routes are enough to get a working endpoint.
Validation is dynamic, driven by `FormRequest` classes rather than static
type annotations. Scaffolding goes through the `dev.py` CLI. AI ergonomics
are the strongest asset — the fixed directory conventions plus the
`.agents/` directory (skills, plans, docs) let an agent orient itself without
reading the whole codebase first.

The competitor comparison in section 2 below covers the trade-offs against
non-convention-based and decorator-heavy alternatives in more detail than a
table could capture accurately, so no comparison matrix is kept here.

---

## 2. Strengths and Weaknesses of Competitors

### A. Reference points
* **DX Strength:** Outstanding developer onboarding. Dynamic Facades and active record models make writing queries and handling requests extremely expressive.
* **AI Challenge:** Loose typing in PHP historically makes it harder for IAs to infer types without reading model definitions and database schemas.

### B. NestJS (TypeScript)
* **DX Strength:** Highly modular and testable.
* **AI Challenge:** Massive context overhead. To add a feature, an AI must modify a controller, a service, a module, and register them. This consumes significant tokens and increases the risk of file-syncing errors.

### C. FastAPI (Python)
* **DX Strength:** Lightning-fast, async-first, automatically generates OpenAPI documentation.
* **AI Challenge:** No conventions. Every project organizes controllers, routers, and models differently, meaning an AI must spend hundreds of tokens parsing the specific project's custom directory structure before writing code.

---

## 3. How Craft Solves the AI & Developer Learning Curve

**Craft** is designed to achieve the best of both worlds:

### 1. Zero-Cognitive-Load Onboarding (For Humans)
Since Craft mirrors a conventional MVC directory structure (`app/Http/Controllers`, `app/Models`, `routes/web.py`), any developer with PHP, Symfony, or Rails experience instantly knows where everything belongs. There is no new architecture paradigm to learn.

### 2. High-Density Context (For AI Agents)
By using a dedicated `.agents/` directory containing **Skills**, **Blueprints**, and **Plans**, AI agents do not need to read the entire codebase to understand conventions.
* The AI simply reads `.agents/skills/framework/craft-development/SKILL.md` to acquire the framework rules in a single turn.

### 3. CLI Scaffolding for AI Agents
Writing code from scratch is error-prone for AIs. By expanding `dev.py` with commands like:
* `python dev.py make:crud <Model>`
The AI agent can simply issue a CLI terminal call to generate the database migration, model, request validation, controller, and routes, and then focus 100% on implementing the core business logic.

---

## 4. Actionable Improvements for Craft's DX

To make the learning curve even better, we propose implementing:

1. **AI-Targeted Code Annotations (AI-hints):**
   Add inline docstrings specifying where related files live (e.g. `# Related Request: app/Http/Requests/StorePostRequest.py`). This acts as pathfinders for AI agents.
2. **Dynamic OpenAPI/Swagger Docs:**
   Use FastAPI's auto-generated Swagger UI (`/docs`) to allow developers to visually inspect and test all routes dynamically.
3. **Interactive Tinker REPL:**
   Expand `dev.py tinker` to start an interactive IPython shell pre-loaded with all models, facades, and container services, letting developers run queries and debug ORM relations in real-time.
